// static/state/store.js

export class Store {
    constructor() {
        this.state = {
            token: localStorage.getItem('jarvis_token') || null,
            user: JSON.parse(localStorage.getItem('jarvis_user')) || null,
            connectionStatus: 'disconnected',
            voiceStatus: 'idle', // 'idle' | 'listening' | 'processing' | 'speaking'
            conversationHistory: [],
            conversationsList: [],
            activeConversationId: null,
            documentsList: [],
            isTyping: false,
            activeUploads: [], // Array of { name, progress, error }
            sessionId: null,
            stats: {
                intent_distribution: {},
                average_confidence: 0,
                fallback_rate: 0,
                average_latency: 0,
                rag_query_count: 0
            }
        };
        this.listeners = new Set();
    }

    subscribe(listener) {
        this.listeners.add(listener);
        return () => {
            this.listeners.delete(listener);
        };
    }

    notify() {
        for (const listener of this.listeners) {
            try {
                listener({ ...this.state });
            } catch (e) {
                console.error('Error in state listener:', e);
            }
        }
    }

    setAuth(token, user) {
        this.state.token = token;
        this.state.user = user;
        if (token) {
            localStorage.setItem('jarvis_token', token);
            localStorage.setItem('jarvis_user', JSON.stringify(user));
        } else {
            localStorage.removeItem('jarvis_token');
            localStorage.removeItem('jarvis_user');
            this.state.conversationsList = [];
            this.state.activeConversationId = null;
            this.state.conversationHistory = [];
            this.state.documentsList = [];
        }
        this.notify();
    }

    setConnectionStatus(status) {
        if (this.state.connectionStatus !== status) {
            this.state.connectionStatus = status;
            this.notify();
        }
    }

    setVoiceStatus(status) {
        if (this.state.voiceStatus !== status) {
            this.state.voiceStatus = status;
            this.notify();
        }
    }

    setSessionId(sessionId) {
        if (this.state.sessionId !== sessionId) {
            this.state.sessionId = sessionId;
            this.notify();
        }
    }

    setIsTyping(isTyping) {
        if (this.state.isTyping !== isTyping) {
            this.state.isTyping = isTyping;
            this.notify();
        }
    }

    setConversationsList(list) {
        this.state.conversationsList = list;
        this.notify();
    }

    setActiveConversationId(id) {
        this.state.activeConversationId = id;
        this.notify();
    }

    setConversationHistory(history) {
        // Map backend Message list to frontend conversation history bubbles
        this.state.conversationHistory = history.map(msg => ({
            id: msg.id,
            sender: msg.sender,
            text: msg.text,
            timestamp: new Date(msg.timestamp),
            source: msg.source,
            confidence: msg.confidence
        }));
        this.notify();
    }

    addMessage(sender, text, metadata = {}) {
        const message = {
            id: Date.now() + Math.random().toString(36).substr(2, 9),
            sender, // 'user' | 'assistant' | 'system'
            text,
            timestamp: new Date(),
            source: metadata.source || null, // 'skill' | 'llm' | 'rag' | 'clarification'
            confidence: metadata.confidence !== undefined ? metadata.confidence : null
        };
        this.state.conversationHistory.push(message);
        this.notify();
        return message;
    }

    setDocumentsList(list) {
        this.state.documentsList = list;
        this.notify();
    }

    addActiveUpload(name) {
        this.state.activeUploads.push({ name, progress: 0, error: null });
        this.notify();
    }

    updateUploadProgress(name, progress) {
        const upload = this.state.activeUploads.find(u => u.name === name);
        if (upload) {
            upload.progress = progress;
            this.notify();
        }
    }

    completeActiveUpload(name) {
        this.state.activeUploads = this.state.activeUploads.filter(u => u.name !== name);
        this.notify();
    }

    failActiveUpload(name, errorMessage) {
        const upload = this.state.activeUploads.find(u => u.name === name);
        if (upload) {
            upload.error = errorMessage;
            upload.progress = 100;
            this.notify();
        }
    }

    clearUploadError(name) {
        this.state.activeUploads = this.state.activeUploads.filter(u => u.name !== name);
        this.notify();
    }

    setStats(stats) {
        this.state.stats = stats;
        this.notify();
    }
}
