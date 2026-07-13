// static/api/rest.js

export class RestClient {
    /**
     * Helper to get header configurations with JWT token
     */
    static getHeaders(hasBody = true) {
        const headers = {};
        if (hasBody) {
            headers['Content-Type'] = 'application/json';
        }
        const token = localStorage.getItem('jarvis_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    }

    // --- AUTHENTICATION ENDPOINTS ---

    static async register(username, password) {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Registration failed');
        }
        return data;
    }

    static async login(username, password) {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Login failed');
        }
        return data; // returns { token, user }
    }

    static async fetchMe() {
        const response = await fetch('/api/auth/me', {
            method: 'GET',
            headers: this.getHeaders(false)
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch user profiles');
        }
        return data.user;
    }

    // --- CONVERSATION ENDPOINTS ---

    static async fetchConversations() {
        const response = await fetch('/api/conversations', {
            headers: this.getHeaders(false)
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch conversations');
        }
        return data.conversations || [];
    }

    static async createConversation(title) {
        const response = await fetch('/api/conversations', {
            method: 'POST',
            headers: this.getHeaders(true),
            body: JSON.stringify({ title })
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to create conversation');
        }
        return data;
    }

    static async fetchMessages(convId) {
        const response = await fetch(`/api/conversations/${convId}/messages`, {
            headers: this.getHeaders(false)
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch messages');
        }
        return data.messages || [];
    }

    static async deleteConversation(convId) {
        const response = await fetch(`/api/conversations/${convId}`, {
            method: 'DELETE',
            headers: this.getHeaders(false)
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to delete conversation');
        }
        return data;
    }

    // --- ANALYTICS ENDPOINT ---

    static async fetchStats() {
        const response = await fetch('/api/analytics/stats', {
            headers: this.getHeaders(false)
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch analytics statistics');
        }
        return data;
    }

    // --- DOCUMENT MANAGEMENT ENDPOINTS ---

    /**
     * Uploads a document to the backend and tracks upload progress.
     */
    static uploadFile(file, sessionId, onProgress) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            formData.append('file', file);
            formData.append('session_id', sessionId || 'default_session');

            xhr.open('POST', '/upload', true);

            // Set Auth headers
            const token = localStorage.getItem('jarvis_token');
            if (token) {
                xhr.setRequestHeader('Authorization', `Bearer ${token}`);
            }

            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable) {
                    const percentComplete = Math.round((event.loaded / event.total) * 100);
                    if (onProgress) onProgress(percentComplete);
                }
            };

            xhr.onload = () => {
                let response = {};
                try {
                    response = JSON.parse(xhr.responseText);
                } catch (e) {
                    response = { error: 'Invalid response from server' };
                }

                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(response);
                } else {
                    reject(new Error(response.error || 'Failed to upload document'));
                }
            };

            xhr.onerror = () => {
                reject(new Error('Network connection error during upload'));
            };

            xhr.send(formData);
        });
    }

    /**
     * Fetches the list of currently indexed documents for this session.
     */
    static async fetchDocuments(sessionId) {
        const headers = this.getHeaders(false);
        const sid = sessionId || 'default_session';
        const response = await fetch(`/documents?session_id=${encodeURIComponent(sid)}`, {
            headers
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch documents');
        }
        return data.documents || [];
    }

    /**
     * Deletes a document from the session and triggers index rebuild.
     */
    static async deleteDocument(sessionId, filename) {
        const headers = this.getHeaders(false);
        const sid = sessionId || 'default_session';
        const response = await fetch(`/documents?session_id=${encodeURIComponent(sid)}&filename=${encodeURIComponent(filename)}`, {
            method: 'DELETE',
            headers
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to delete document');
        }
        return data;
    }
}
