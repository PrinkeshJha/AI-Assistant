// static/components/voice-control.js

export class VoiceControl {
    constructor(orbContainerId, orbGlowId, statusTextId, hintId, visualizerId, interruptBtnId, store, socketClient) {
        this.orbContainer = document.getElementById(orbContainerId);
        this.orbGlow = document.getElementById(orbGlowId);
        this.statusText = document.getElementById(statusTextId);
        this.hintText = document.getElementById(hintId);
        this.visualizer = document.getElementById(visualizerId);
        this.interruptBtn = document.getElementById(interruptBtnId);
        
        this.store = store;
        this.socketClient = socketClient;
        this.recognition = null;
        this.currentUtterance = null;
        
        // Flag to check if the last message was sent via voice
        this.triggeredByVoice = false;

        this.initSpeechRecognition();
        this.initVisualizer();

        // Bind events
        if (this.orbContainer) {
            this.orbContainer.addEventListener('click', () => this.handleOrbClick());
        }
        if (this.interruptBtn) {
            this.interruptBtn.addEventListener('click', () => this.stopSpeaking());
        }

        // Subscribe to store updates
        this.store.subscribe((state) => this.updateUI(state));
    }

    initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.lang = 'en-US';
            this.recognition.interimResults = false;

            this.recognition.onstart = () => {
                this.store.setVoiceStatus('listening');
            };

            this.recognition.onresult = (event) => {
                const command = event.results[0][0].transcript;
                console.log('Speech recognition result:', command);
                this.triggeredByVoice = true;
                
                // Add message to chat log, trigger loading state, send to server
                this.store.addMessage('user', command);
                this.store.setIsTyping(true);
                this.store.setVoiceStatus('processing');
                this.socketClient.sendCommand(command);
            };

            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                if (event.error !== 'no-speech') {
                    this.store.addMessage('system', `Voice Recognition Error: ${event.error}`);
                }
                this.store.setVoiceStatus('idle');
            };

            this.recognition.onend = () => {
                // If it ended and we didn't transition to processing or speaking, go back to idle
                setTimeout(() => {
                    const currentStatus = this.store.state.voiceStatus;
                    if (currentStatus === 'listening') {
                        this.store.setVoiceStatus('idle');
                    }
                }, 200);
            };
        } else {
            console.warn('Web Speech Recognition API is not supported in this browser.');
        }
    }

    initVisualizer() {
        if (!this.visualizer) return;
        this.visualizer.innerHTML = '';
        // Create 20 visualizer bars
        for (let i = 0; i < 20; i++) {
            const bar = document.createElement('div');
            bar.className = 'visualizer-bar';
            // Randomize animation delays for realistic movement
            bar.style.animationDelay = `${Math.random() * 0.8}s`;
            // Randomize heights
            bar.style.height = `${Math.random() * 100}%`;
            this.visualizer.appendChild(bar);
        }
    }

    handleOrbClick() {
        const connection = this.store.state.connectionStatus;
        if (connection !== 'connected') {
            alert('Cannot start voice control. You are disconnected.');
            return;
        }

        const currentStatus = this.store.state.voiceStatus;

        if (currentStatus === 'speaking') {
            this.stopSpeaking();
        } else if (currentStatus === 'listening') {
            this.stopListening();
        } else if (currentStatus === 'idle') {
            this.startListening();
        }
    }

    startListening() {
        if (this.recognition) {
            try {
                // Stop any playing speech first
                window.speechSynthesis.cancel();
                this.recognition.start();
            } catch (e) {
                console.warn('SpeechRecognition failed to start:', e);
            }
        } else {
            alert('Speech Recognition is not supported by your browser. Please type commands instead.');
        }
    }

    stopListening() {
        if (this.recognition) {
            try {
                this.recognition.abort();
                this.store.setVoiceStatus('idle');
            } catch (e) {
                console.error(e);
            }
        }
    }

    /**
     * Synthesizes and speaks text out loud.
     * @param {string} text 
     * @param {boolean} awakeState - If true, auto-starts listening after speaking completes
     */
    speak(text, awakeState = false) {
        // Stop any current speech
        window.speechSynthesis.cancel();

        // Strip HTML tags for clean speech synthesis
        const cleanText = text.replace(/<\/?[^>]+(>|$)/g, "");

        this.currentUtterance = new SpeechSynthesisUtterance(cleanText);
        this.store.setVoiceStatus('speaking');

        this.currentUtterance.onend = () => {
            console.log('Speech playback completed');
            this.store.setVoiceStatus('idle');
            
            // If Jarvis backend returned AWAKE, keep listening
            if (awakeState) {
                this.startListening();
            }
        };

        this.currentUtterance.onerror = (e) => {
            console.error('Speech synthesis error:', e);
            this.store.setVoiceStatus('idle');
        };

        window.speechSynthesis.speak(this.currentUtterance);
    }

    stopSpeaking() {
        window.speechSynthesis.cancel();
        this.store.setVoiceStatus('idle');
    }

    /**
     * Returns true if the last command was triggered via voice.
     */
    wasVoiceTriggered() {
        return this.triggeredByVoice;
    }

    /**
     * Resets the voice trigger flag after a response is processed.
     */
    clearVoiceTriggered() {
        this.triggeredByVoice = false;
    }

    updateUI(state) {
        const voiceState = state.voiceStatus;
        const connection = state.connectionStatus;
        
        // Map states to colors and visual descriptions
        const container = this.orbContainer.parentElement; // .voice-section
        if (container) {
            container.className = `voice-section state-${voiceState}`;
        }

        // Handle connection drop
        if (connection !== 'connected') {
            this.statusText.textContent = 'SYSTEM offline';
            this.statusText.style.color = 'var(--color-error)';
            this.hintText.textContent = 'Jarvis core link lost.';
            this.interruptBtn.classList.remove('visible');
            this.visualizer.classList.remove('visible');
            return;
        }

        this.statusText.style.color = '';

        if (voiceState === 'idle') {
            this.statusText.textContent = 'SYSTEM READY';
            this.hintText.textContent = 'Tap Orb or say "Jarvis" to begin';
            this.interruptBtn.classList.remove('visible');
            this.visualizer.classList.remove('visible');
        } else if (voiceState === 'listening') {
            this.statusText.textContent = 'LISTENING...';
            this.hintText.textContent = 'Jarvis is capturing your voice input';
            this.interruptBtn.classList.remove('visible');
            this.visualizer.classList.remove('visible');
        } else if (voiceState === 'processing') {
            this.statusText.textContent = 'THINKING...';
            this.hintText.textContent = 'Resolving intent classification';
            this.interruptBtn.classList.remove('visible');
            this.visualizer.classList.remove('visible');
        } else if (voiceState === 'speaking') {
            this.statusText.textContent = 'JARVIS SPEAKING';
            this.hintText.textContent = 'Tap Orb to interrupt/stop playback';
            this.interruptBtn.classList.add('visible');
            this.visualizer.classList.add('visible');
        }
    }
}
