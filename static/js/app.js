// static/js/app.js
import { Store } from '../state/store.js';
import { SocketClient } from '../api/socket.js';
import { RestClient } from '../api/rest.js';
import { AuthComponent } from '../components/auth.js';
import { ConnectionIndicator } from '../components/connection-indicator.js';
import { ChatWindow } from '../components/chat-window.js';
import { VoiceControl } from '../components/voice-control.js';
import { UploadDrawer } from '../components/upload-drawer.js';

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize State Store
    const store = new Store();
    let socketClient = null;
    let chatWindow = null;
    let voiceControl = null;
    let uploadDrawer = null;
    let connectionIndicator = null;

    // Helper to start the socket and components after authentication
    const initializeAppComponents = () => {
        // Disconnect old socket if exists
        if (socketClient) {
            socketClient.disconnect();
        }

        // Initialize Socket.IO Client with handlers
        socketClient = new SocketClient(
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
                let messageText = data.message;

                // Handle client-side open url actions emitted by backend skills
                if (messageText.startsWith('[ACTION:OPEN_URL]')) {
                    const url = messageText.replace('[ACTION:OPEN_URL]', '').trim();
                    messageText = `Opening URL: <a href="${url}" target="_blank" class="chat-link">${url}</a>`;
                    
                    // Trigger browser open
                    window.open(url, '_blank');
                    
                    if (voiceControl && voiceControl.wasVoiceTriggered()) {
                        voiceControl.speak("Opening requested link.", data.state === 'AWAKE');
                    }
                } else {
                    // Only speak via TTS if the command was voice-triggered
                    if (voiceControl && voiceControl.wasVoiceTriggered()) {
                        voiceControl.speak(messageText, data.state === 'AWAKE');
                    }
                }
                
                // Add response to conversation history
                store.addMessage('assistant', messageText, {
                    source: data.source,
                    confidence: data.confidence
                });

                if (voiceControl) {
                    voiceControl.clearVoiceTriggered();
                }
            }
        );

        // Connect socket
        socketClient.connect();

        // Bind Connection badge
        if (!connectionIndicator) {
            connectionIndicator = new ConnectionIndicator('connection-status-badge', store);
        }

        // Bind Chat Log Window
        if (!chatWindow) {
            chatWindow = new ChatWindow(
                'chat-message-log', 
                'chat-message-input', 
                'chat-send-btn', 
                store, 
                socketClient
            );
        } else {
            // Update reference
            chatWindow.socketClient = socketClient;
        }

        // Bind Voice Controls
        if (!voiceControl) {
            voiceControl = new VoiceControl(
                'ai-orb',
                'orb-glow-elem',
                'orb-status-text',
                'orb-hint-text',
                'audio-visualizer',
                'orb-interrupt-btn',
                store,
                socketClient
            );
        } else {
            // Update reference
            voiceControl.socketClient = socketClient;
        }

        // Bind Upload Drawer
        if (!uploadDrawer) {
            uploadDrawer = new UploadDrawer(
                'upload-dropzone',
                'upload-file-input',
                'active-uploads-container',
                'indexed-documents-list',
                store
            );
        }

        // Set User Display details
        if (store.state.user) {
            document.getElementById('user-display-name').textContent = store.state.user.username;
        }

        // Load initial user threads and documents
        loadUserChats();
        loadAnalyticsStats();
    };

    // Load User Conversations
    const loadUserChats = async () => {
        try {
            const convs = await RestClient.fetchConversations();
            store.setConversationsList(convs);
            
            // Set first conversation as active if none set
            if (convs.length > 0 && !store.state.activeConversationId) {
                switchConversation(convs[0].id);
            }
        } catch (err) {
            console.error('Failed to load user conversations:', err);
        }
    };

    // Switch Active Conversation
    const switchConversation = async (convId) => {
        store.setActiveConversationId(convId);
        const listContainer = document.getElementById('conversations-list');
        
        // Find active conversation object
        const activeConv = store.state.conversationsList.find(c => c.id === convId);
        if (activeConv) {
            document.getElementById('active-chat-title').textContent = activeConv.title;
        }

        try {
            // Fetch messages from backend
            const msgs = await RestClient.fetchMessages(convId);
            store.setConversationHistory(msgs);
            
            // Re-render chats window list
            if (chatWindow) {
                chatWindow.renderedMessagesCount = 0;
                document.getElementById('chat-message-log').innerHTML = '';
                chatWindow.render(store.state);
            }
        } catch (err) {
            console.error(`Failed to load messages for conversation ${convId}:`, err);
        }
    };

    // Load Stats Dashboard Metrics
    const loadAnalyticsStats = async () => {
        try {
            const stats = await RestClient.fetchStats();
            store.setStats(stats);
        } catch (err) {
            console.error('Failed to load system metrics:', err);
        }
    };

    // Render conversations list in sidebar
    const renderConversations = (state) => {
        const container = document.getElementById('conversations-list');
        if (!container) return;

        container.innerHTML = '';
        if (state.conversationsList.length === 0) {
            container.innerHTML = `<div class="no-chats-placeholder">No conversations yet</div>`;
            return;
        }

        state.conversationsList.forEach(c => {
            const item = document.createElement('div');
            const isActive = c.id === state.activeConversationId;
            item.className = `conversation-item ${isActive ? 'active' : ''}`;
            
            item.innerHTML = `
                <div class="chat-icon">💬</div>
                <div class="chat-details" title="${c.title}">
                    <span class="chat-title">${c.title}</span>
                </div>
                <button class="delete-chat-btn" data-id="${c.id}" title="Delete session">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            `;

            // Click event to switch
            item.addEventListener('click', (e) => {
                // Ensure delete button click doesn't trigger switch
                if (e.target.closest('.delete-chat-btn')) return;
                switchConversation(c.id);
            });

            // Delete event
            const delBtn = item.querySelector('.delete-chat-btn');
            delBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (confirm(`Are you sure you want to delete conversation session "${c.title}"?`)) {
                    try {
                        await RestClient.deleteConversation(c.id);
                        // If deleted conversation was active, reset active conversation
                        if (c.id === store.state.activeConversationId) {
                            store.setActiveConversationId(null);
                        }
                        loadUserChats();
                    } catch (err) {
                        alert(`Failed to delete conversation: ${err.message}`);
                    }
                }
            });

            container.appendChild(item);
        });
    };

    // Render system stats overlay
    const renderStatsModal = (state) => {
        const stats = state.stats;
        document.getElementById('stat-fallback-rate').textContent = `${(stats.fallback_rate * 100).toFixed(1)}%`;
        document.getElementById('stat-avg-latency').textContent = `${stats.average_latency.toFixed(2)}s`;
        document.getElementById('stat-avg-confidence').textContent = `${(stats.average_confidence * 100).toFixed(1)}%`;
        document.getElementById('stat-rag-count').textContent = stats.rag_query_count;

        const tableBody = document.querySelector('#intent-distribution-table tbody');
        if (tableBody) {
            tableBody.innerHTML = '';
            const intents = Object.entries(stats.intent_distribution);
            if (intents.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="2" style="text-align: center;">No metrics captured yet</td></tr>`;
                return;
            }
            intents.forEach(([intent, count]) => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><strong>${intent}</strong></td>
                    <td>${count}</td>
                `;
                tableBody.appendChild(row);
            });
        }
    };

    // 2. Initialize Auth Component
    const auth = new AuthComponent(
        'auth-panel',
        'app-viewport',
        store,
        // Success callback
        () => {
            initializeAppComponents();
        }
    );

    // Subscribe to store updates to render conversations and stats
    store.subscribe((state) => {
        renderConversations(state);
        renderStatsModal(state);
    });

    // 3. Bind UI interactions for Main SaaS Dashboard
    
    // Create new conversation
    const newChatBtn = document.getElementById('new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', async () => {
            const title = prompt('Enter a title for this conversation session:');
            if (title && title.trim()) {
                try {
                    const newConv = await RestClient.createConversation(title.trim());
                    // Refresh chats and switch to the new one
                    await loadUserChats();
                    switchConversation(newConv.id);
                } catch (err) {
                    alert(`Failed to create conversation: ${err.message}`);
                }
            }
        });
    }

    // Toggle stats overlay modal
    const viewStatsBtn = document.getElementById('view-stats-btn');
    const statsModal = document.getElementById('stats-modal');
    const closeStatsBtn = document.getElementById('close-stats-modal-btn');

    if (viewStatsBtn && statsModal) {
        viewStatsBtn.addEventListener('click', async () => {
            await loadAnalyticsStats();
            statsModal.style.display = 'flex';
        });
    }

    if (closeStatsBtn && statsModal) {
        closeStatsBtn.addEventListener('click', () => {
            statsModal.style.display = 'none';
        });
        
        // Close modal when clicking background overlay
        statsModal.addEventListener('click', (e) => {
            if (e.target === statsModal) {
                statsModal.style.display = 'none';
            }
        });
    }

    // Logout trigger
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            if (confirm('Disconnect security credentials and sign out of Jarvis Core?')) {
                // Clear store credentials and reset
                store.setAuth(null, null);
                if (socketClient) {
                    socketClient.disconnect();
                }
            }
        });
    }

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

    // Auto-bootstrap app if token exists on load
    if (store.state.token) {
        initializeAppComponents();
    }
});
