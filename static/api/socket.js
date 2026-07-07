// static/api/socket.js

export class SocketClient {
    constructor(onStatusChange, onMessageReceived) {
        this.socket = null;
        this.onStatusChange = onStatusChange;
        this.onMessageReceived = onMessageReceived;
    }

    connect() {
        // io() is imported globally via templates/jarvis_ui.html
        this.socket = io({
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000,
        });

        this.socket.on('connect', () => {
            console.log('SocketConnected, ID:', this.socket.id);
            this.onStatusChange('connected');
        });

        this.socket.on('disconnect', (reason) => {
            console.warn('SocketDisconnected. Reason:', reason);
            this.onStatusChange('disconnected');
        });

        this.socket.on('connect_error', (error) => {
            console.error('Socket Connection Error:', error);
            this.onStatusChange('connecting'); // Reconnection attempts are in progress
        });

        this.socket.on('reconnect_attempt', (attempt) => {
            console.log(`Reconnection attempt #${attempt}`);
            this.onStatusChange('connecting');
        });

        this.socket.on('reconnect_failed', () => {
            console.error('Reconnection failed completely');
            this.onStatusChange('disconnected');
        });

        this.socket.on('assistant_response', (data) => {
            console.log('SocketReceivedResponse:', data);
            this.onMessageReceived(data);
        });
    }

    sendCommand(command) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('user_command', { command });
            return true;
        }
        console.error('Cannot send command. Socket is not connected.');
        return false;
    }

    getSessionId() {
        return this.socket ? this.socket.id : null;
    }
}
