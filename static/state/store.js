// static/state/store.js

export class Store {
    constructor() {
        this.state = {
            connectionStatus: 'disconnected',
            voiceStatus: 'idle', // 'idle' | 'listening' | 'processing' | 'speaking'
            conversationHistory: [],
            documentsList: [],
            isTyping: false,
            activeUploads: [], // Array of { name, progress, error }
            sessionId: null
        };
        this.listeners = new Set();
    }

    subscribe(listener) {
        this.listeners.add(listener);
        // Return unsubscribe function
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
}
