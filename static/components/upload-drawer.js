// static/components/upload-drawer.js
import { RestClient } from '../api/rest.js';

export class UploadDrawer {
    constructor(dropzoneId, fileInputId, uploadsContainerId, docsContainerId, store) {
        this.dropzone = document.getElementById(dropzoneId);
        this.fileInput = document.getElementById(fileInputId);
        this.uploadsContainer = document.getElementById(uploadsContainerId);
        this.docsContainer = document.getElementById(docsContainerId);
        this.store = store;

        // Session tracking
        this.lastSessionId = null;

        // Bind events
        if (this.dropzone) {
            this.dropzone.addEventListener('click', () => this.fileInput.click());
            this.dropzone.addEventListener('dragover', (e) => this.handleDragOver(e));
            this.dropzone.addEventListener('dragleave', () => this.handleDragLeave());
            this.dropzone.addEventListener('drop', (e) => this.handleDrop(e));
        }

        if (this.fileInput) {
            this.fileInput.addEventListener('change', () => this.handleFileSelect());
        }

        // Subscribe to store updates
        this.store.subscribe((state) => {
            this.render(state);
            this.checkSessionLoad(state);
        });
    }

    handleDragOver(e) {
        e.preventDefault();
        this.dropzone.classList.add('dragover');
    }

    handleDragLeave() {
        this.dropzone.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        this.dropzone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.uploadFile(files[0]);
        }
    }

    handleFileSelect() {
        const files = this.fileInput.files;
        if (files.length > 0) {
            this.uploadFile(files[0]);
            this.fileInput.value = ''; // Reset
        }
    }

    checkSessionLoad(state) {
        // Load documents list when we obtain a valid session ID for the first time
        if (state.connectionStatus === 'connected' && state.sessionId && state.sessionId !== this.lastSessionId) {
            this.lastSessionId = state.sessionId;
            this.loadDocuments();
        }
    }

    async loadDocuments() {
        const sessionId = this.store.state.sessionId;
        if (!sessionId) return;

        try {
            const docs = await RestClient.fetchDocuments(sessionId);
            this.store.setDocumentsList(docs);
        } catch (err) {
            console.error('Failed to load documents:', err);
        }
    }

    uploadFile(file) {
        const sessionId = this.store.state.sessionId;
        const connection = this.store.state.connectionStatus;

        if (connection !== 'connected') {
            alert('Cannot upload document. You are currently disconnected from Jarvis.');
            return;
        }

        // Validate file type
        const ext = file.name.split('.').pop().toLowerCase();
        const allowed = ['txt', 'pdf', 'docx'];
        if (!allowed.includes(ext)) {
            alert('Invalid file format. Only PDF, TXT, and DOCX files are allowed.');
            return;
        }

        // Validate file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
            alert('File size exceeds the 10MB limit.');
            return;
        }

        this.store.addActiveUpload(file.name);

        RestClient.uploadFile(file, sessionId, (progress) => {
            this.store.updateUploadProgress(file.name, progress);
        })
        .then((response) => {
            this.store.completeActiveUpload(file.name);
            this.store.addMessage('system', `Successfully uploaded and indexed: ${file.name} (${response.chunks} chunks).`);
            this.loadDocuments();
        })
        .catch((err) => {
            console.error(err);
            this.store.failActiveUpload(file.name, err.message);
            this.store.addMessage('system', `Failed to upload and index ${file.name}: ${err.message}`);
        });
    }

    async deleteDoc(filename) {
        const sessionId = this.store.state.sessionId;
        if (!sessionId) return;

        const confirmDelete = confirm(`Are you sure you want to delete and un-index ${filename}?`);
        if (!confirmDelete) return;

        this.store.addMessage('system', `Deleting ${filename} and rebuilding vector store index...`);

        try {
            const response = await RestClient.deleteDocument(sessionId, filename);
            this.store.addMessage('system', response.message);
            this.loadDocuments();
        } catch (err) {
            console.error(err);
            this.store.addMessage('system', `Failed to delete ${filename}: ${err.message}`);
        }
    }

    render(state) {
        // Render Active Upload progress bars
        if (this.uploadsContainer) {
            this.uploadsContainer.innerHTML = '';
            state.activeUploads.forEach(upload => {
                const item = document.createElement('div');
                item.className = 'upload-progress-item';
                
                let errorHTML = '';
                if (upload.error) {
                    errorHTML = `
                        <div class="upload-error-message">
                            <span>Error: ${upload.error}</span>
                            <span class="error-dismiss" data-name="${this.escapeHTML(upload.name)}">Dismiss</span>
                        </div>
                    `;
                }

                item.innerHTML = `
                    <div class="progress-header">
                        <span>${this.escapeHTML(upload.name)}</span>
                        <span>${upload.progress}%</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-bar" style="width: ${upload.progress}%"></div>
                    </div>
                    ${errorHTML}
                `;

                // Handle dismiss click
                const dismiss = item.querySelector('.error-dismiss');
                if (dismiss) {
                    dismiss.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const name = e.target.getAttribute('data-name');
                        this.store.clearUploadError(name);
                    });
                }

                this.uploadsContainer.appendChild(item);
            });
        }

        // Render Indexed Documents List
        if (this.docsContainer) {
            this.docsContainer.innerHTML = '';
            
            if (state.documentsList.length === 0) {
                this.docsContainer.innerHTML = `
                    <div class="no-documents-state">
                        <span>No files currently indexed</span>
                    </div>
                `;
                return;
            }

            state.documentsList.forEach(doc => {
                const item = document.createElement('div');
                item.className = 'document-item';

                // Convert bytes to user friendly size
                const sizeKB = (doc.size / 1024).toFixed(1);

                item.innerHTML = `
                    <div class="doc-info">
                        <span class="doc-name" title="${this.escapeHTML(doc.name)}">${this.escapeHTML(doc.name)}</span>
                        <span class="doc-size">${sizeKB} KB</span>
                    </div>
                    <button class="delete-doc-btn" data-name="${this.escapeHTML(doc.name)}" title="Delete Document">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    </button>
                `;

                const delBtn = item.querySelector('.delete-doc-btn');
                delBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const name = e.target.closest('.delete-doc-btn').getAttribute('data-name');
                    this.deleteDoc(name);
                });

                this.docsContainer.appendChild(item);
            });
        }
    }

    escapeHTML(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
