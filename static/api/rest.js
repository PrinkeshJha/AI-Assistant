// static/api/rest.js

export class RestClient {
    /**
     * Uploads a document to the backend and tracks upload progress.
     * @param {File} file 
     * @param {string} sessionId 
     * @param {function(number)} onProgress - Callback with percentage progress (0 to 100)
     * @returns {Promise<any>}
     */
    static uploadFile(file, sessionId, onProgress) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            formData.append('file', file);
            formData.append('session_id', sessionId || 'default_session');

            xhr.open('POST', '/upload', true);

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
     * @param {string} sessionId 
     * @returns {Promise<Array>}
     */
    static async fetchDocuments(sessionId) {
        const sid = sessionId || 'default_session';
        const response = await fetch(`/documents?session_id=${encodeURIComponent(sid)}`);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch documents');
        }
        return data.documents || [];
    }

    /**
     * Deletes a document from the session and triggers index rebuild.
     * @param {string} sessionId 
     * @param {string} filename 
     * @returns {Promise<any>}
     */
    static async deleteDocument(sessionId, filename) {
        const sid = sessionId || 'default_session';
        const response = await fetch(`/documents?session_id=${encodeURIComponent(sid)}&filename=${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to delete document');
        }
        return data;
    }
}
