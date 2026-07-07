// static/js/app.js
import { Store } from '../state/store.js';
import { SocketClient } from '../api/socket.js';
import { ConnectionIndicator } from '../components/connection-indicator.js';
import { ChatWindow } from '../components/chat-window.js';
import { VoiceControl } from '../components/voice-control.js';
import { UploadDrawer } from '../components/upload-drawer.js';

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize State Store
    const store = new Store();

    // 2. Initialize Socket.IO Client with handlers
    const socketClient = new SocketClient(
        // Status change handler
        (status) => {
            store.setConnectionStatus(status);
            if (status === 'connected') {
                store.setSessionId(socketClient.getSessionId());
            } else {
                store.setSessionId(null);
            }
        },
        // Message received handler
        (data) => {
            store.setIsTyping(false);
            
            // Add response to conversation history
            store.addMessage('assistant', data.message, {
                source: data.source,
                confidence: data.confidence
            });

            // Only speak via TTS if the command was voice-triggered
            if (voiceControl.wasVoiceTriggered()) {
                voiceControl.speak(data.message, data.state === 'AWAKE');
            }
            voiceControl.clearVoiceTriggered();
        }
    );

    // Connect to server
    socketClient.connect();

    // 3. Mount UI Components
    new ConnectionIndicator('connection-status-badge', store);
    
    new ChatWindow(
        'chat-message-log', 
        'chat-message-input', 
        'chat-send-btn', 
        store, 
        socketClient
    );

    const voiceControl = new VoiceControl(
        'ai-orb',
        'orb-glow-elem',
        'orb-status-text',
        'orb-hint-text',
        'audio-visualizer',
        'orb-interrupt-btn',
        store,
        socketClient
    );

    new UploadDrawer(
        'upload-dropzone',
        'upload-file-input',
        'active-uploads-container',
        'indexed-documents-list',
        store
    );

    // 4. Handle Mobile Responsive Sidebar Toggle
    const sidebarToggle = document.getElementById('sidebar-toggle-btn');
    const sidebar = document.getElementById('sidebar-panel');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('open');
            sidebarToggle.textContent = sidebar.classList.contains('open') ? 'Close Panel' : 'Manage Docs';
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 900 && sidebar.classList.contains('open')) {
                if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                    sidebar.classList.remove('open');
                    sidebarToggle.textContent = 'Manage Docs';
                }
            }
        });
    }
});
