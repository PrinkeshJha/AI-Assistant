// static/components/chat-window.js

export class ChatWindow {
    constructor(containerId, inputId, sendBtnId, store, socketClient) {
        this.container = document.getElementById(containerId);
        this.input = document.getElementById(inputId);
        this.sendBtn = document.getElementById(sendBtnId);
        this.store = store;
        this.socketClient = socketClient;

        // Bind events
        this.sendBtn.addEventListener('click', () => this.handleSend());
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSend();
        });

        // Map of skill class names to user-friendly queries
        this.skillQueries = {
            'WeatherSkill': { label: 'Weather Forecast', cmd: 'weather' },
            'NewsSkill': { label: 'Top News', cmd: 'news' },
            'WikiSkill': { label: 'Search Wikipedia', cmd: 'search wikipedia' },
            'TimeSkill': { label: 'Check Time', cmd: 'what time is it' },
            'FunSkill': { label: 'Tell a Joke', cmd: 'tell me a joke' },
            'SystemSkill': { label: 'System Commands', cmd: 'help system' },
            'RAGSkill': { label: 'Search My Notes', cmd: 'search notes' },
            'HelpSkill': { label: 'Help Menu', cmd: 'help' }
        };

        // Subscribe to store updates
        this.store.subscribe((state) => this.render(state));
        
        // Track the length of history to only animate new messages
        this.renderedMessagesCount = 0;
    }

    handleSend() {
        const command = this.input.value.trim();
        const connection = this.store.state.connectionStatus;

        if (connection !== 'connected') {
            alert('Cannot send command. You are currently disconnected from Jarvis.');
            return;
        }

        if (command) {
            // Add user message to store
            this.store.addMessage('user', command);
            // Set typing state
            this.store.setIsTyping(true);
            // Send via socket
            const activeConvId = this.store.state.activeConversationId;
            const sent = this.socketClient.sendCommand(command, activeConvId);
            if (sent) {
                this.input.value = '';
            } else {
                this.store.setIsTyping(false);
            }
        }
    }

    sendSuggestion(command) {
        this.store.addMessage('user', command);
        this.store.setIsTyping(true);
        const activeConvId = this.store.state.activeConversationId;
        this.socketClient.sendCommand(command, activeConvId);
    }

    render(state) {
        if (!this.container) return;

        // Enable/disable input based on connection and busy states
        const isOffline = state.connectionStatus !== 'connected';
        const isBusy = isOffline || state.isTyping || state.voiceStatus === 'listening' || state.voiceStatus === 'speaking';
        this.input.disabled = isBusy;
        this.sendBtn.disabled = isBusy;
        
        if (isOffline) {
            this.input.placeholder = 'Disconnected from server...';
        } else if (state.voiceStatus === 'listening') {
            this.input.placeholder = 'Listening to voice input...';
        } else if (state.voiceStatus === 'speaking') {
            this.input.placeholder = 'Jarvis is speaking...';
        } else if (state.isTyping) {
            this.input.placeholder = 'Jarvis is processing...';
        } else {
            this.input.placeholder = 'Type a command to Jarvis...';
        }

        // Remove previous typing indicator if present
        const existingTyping = this.container.querySelector('.typing-wrapper');
        if (existingTyping) existingTyping.remove();

        // Incrementally append only new messages (avoids full re-render)
        const newMessages = state.conversationHistory.slice(this.renderedMessagesCount);
        newMessages.forEach((msg) => {
            const wrapper = this.createMessageElement(msg);
            this.container.appendChild(wrapper);
        });

        // Render typing indicator if active
        if (state.isTyping) {
            const typingWrapper = document.createElement('div');
            typingWrapper.className = 'message-wrapper assistant typing-wrapper';
            
            const typingBubble = document.createElement('div');
            typingBubble.className = 'message-bubble source-skill';
            typingBubble.innerHTML = `
                <div class="bubble-meta">Jarvis is thinking</div>
                <div class="typing-indicator">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            `;
            typingWrapper.appendChild(typingBubble);
            this.container.appendChild(typingWrapper);
        }

        // Update count of rendered messages
        this.renderedMessagesCount = state.conversationHistory.length;

        // Auto scroll to bottom if new content was added
        if (newMessages.length > 0 || state.isTyping) {
            this.scrollToBottom();
        }
    }

    createMessageElement(msg) {
        const wrapper = document.createElement('div');
        const isUser = msg.sender === 'user';
        
        wrapper.className = `message-wrapper ${isUser ? 'user' : msg.sender}`;
        wrapper.style.animationDelay = '0.05s';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        if (isUser) {
            bubble.innerHTML = `
                <div class="bubble-meta">You</div>
                <p class="message-text">${this.escapeHTML(msg.text)}</p>
            `;
        } else if (msg.sender === 'assistant') {
            const source = msg.source || 'skill';
            bubble.classList.add(`source-${source}`);

            // Render transparency badges
            let badgeHTML = '';
            if (source === 'skill') badgeHTML = '<span class="source-badge skill">Skill Engine</span>';
            if (source === 'llm') badgeHTML = '<span class="source-badge llm">LLM Fallback</span>';
            if (source === 'rag') badgeHTML = '<span class="source-badge rag">Document QA (RAG)</span>';
            if (source === 'clarification') badgeHTML = '<span class="source-badge clarification">Clarification</span>';

            let confHTML = '';
            if (msg.confidence !== null && msg.confidence > 0) {
                confHTML = `<span class="confidence-score">Conf: ${(msg.confidence * 100).toFixed(0)}%</span>`;
            }

            bubble.innerHTML = `
                <div class="bubble-meta">
                    <span>Jarvis</span>
                    <div>
                        ${badgeHTML}
                        ${confHTML}
                    </div>
                </div>
                <p class="message-text">${msg.text}</p>
            `;

            // If clarification message, render clickable suggestion buttons
            if (source === 'clarification') {
                const skillMatches = msg.text.match(/\b[A-Za-z]+Skill\b/g);
                if (skillMatches && skillMatches.length > 0) {
                    const suggestionsDiv = document.createElement('div');
                    suggestionsDiv.className = 'suggestions-grid';
                    
                    skillMatches.forEach(skillName => {
                        const config = this.skillQueries[skillName];
                        if (config) {
                            const btn = document.createElement('button');
                            btn.className = 'suggestion-btn';
                            btn.textContent = config.label;
                            btn.addEventListener('click', () => this.sendSuggestion(config.cmd));
                            suggestionsDiv.appendChild(btn);
                        }
                    });
                    bubble.appendChild(suggestionsDiv);
                }
            }
        } else {
            // System messages
            bubble.innerHTML = `<p class="message-text">${msg.text}</p>`;
        }

        wrapper.appendChild(bubble);
        return wrapper;
    }

    scrollToBottom() {
        this.container.scrollTop = this.container.scrollHeight;
    }

    escapeHTML(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
