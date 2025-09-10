document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const fileInputText = document.querySelector('.file-input-text');
    const documentsList = document.getElementById('documents-list');

    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            fileInputText.textContent = this.files[0].name;
        } else {
            fileInputText.textContent = 'Choose file';
        }
    });

    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        try {
            const response = await fetch('/document', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                showMessage('File uploaded successfully!', 'success');
                loadDocuments();
                fileInput.value = '';
                fileInputText.textContent = 'Choose file';
            } else {
                const error = await response.json();
                showMessage(`Upload failed: ${error.detail}`, 'error');
            }
        } catch (error) {
            showMessage(`Upload failed: ${error.message}`, 'error');
        }
    });

    function showMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = message;

        const container = document.querySelector('.container');
        container.insertBefore(messageDiv, container.firstChild);

        setTimeout(() => {
            messageDiv.remove();
        }, 5000);
    }

    async function loadDocuments() {
        try {
            const response = await fetch('/document/list');
            const documents = await response.json();

            if (documents.length === 0) {
                documentsList.innerHTML = '<div class="loading">No documents uploaded yet.</div>';
                return;
            }

            documentsList.innerHTML = documents.map(doc => `
                <div class="document-item" onclick="showDocumentDetails(${doc.id}, '${doc.name}', '${doc.status}', '${doc.summary || 'No summary available'}')">
                    <div class="document-info">
                        <div class="document-name">${doc.name}</div>
                        <div class="document-meta">
                            Type: ${doc.type} |
                            Created: ${new Date(doc.created_at).toLocaleDateString()}
                        </div>
                    </div>
                    <div class="document-actions">
                        <span class="status status-${doc.status.toLowerCase()}">${doc.status}</span>
                        ${doc.status === 'completed' ?
                            `<button class="chat-btn" onclick="event.stopPropagation(); openChat(${doc.id})">Chat</button>` :
                            `<button class="chat-btn disabled" disabled title="Document must be completed to start chat">Chat</button>`
                        }
                        <button class="delete-doc-btn" onclick="event.stopPropagation(); showDeleteDocumentConfirmation(${doc.id}, '${doc.name}')" title="Delete document">🗑️</button>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            documentsList.innerHTML = '<div class="error">Failed to load documents</div>';
        }
    }

    window.openChat = function(documentId) {
        window.location.href = `/chat/${documentId}`;
    };

    window.showDocumentDetails = function(documentId, name, status, summary) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${name}</h3>
                    <button class="close-btn" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="document-details">
                        <div class="detail-row">
                            <strong>Status:</strong>
                            <span class="status status-${status.toLowerCase()}">${status}</span>
                        </div>
                        <div class="detail-row">
                            <strong>Summary:</strong>
                            <div class="summary-text">${summary}</div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    ${status === 'completed' ?
                        `<button class="chat-btn" onclick="openChat(${documentId}); this.closest('.modal-overlay').remove();">Start Chat</button>` :
                        `<button class="chat-btn disabled" disabled>Chat Not Available</button>`
                    }
                    <button class="close-btn secondary" onclick="this.closest('.modal-overlay').remove()">Close</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    };

    function showDeleteDocumentConfirmation(documentId, documentName) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Delete Document</h3>
                    <button class="close-btn" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <p>Are you sure you want to delete the document "<strong>${documentName}</strong>"? This action cannot be undone and will also delete all associated sessions and chat history.</p>
                </div>
                <div class="modal-footer">
                    <button class="cancel-delete-btn" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                    <button class="confirm-delete-btn" onclick="deleteDocument(${documentId})">Delete</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    async function deleteDocument(documentId) {
        try {
            const response = await fetch(`/document/${documentId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                const modal = document.querySelector('.modal-overlay');
                if (modal) modal.remove();

                showMessage('Document deleted successfully!', 'success');
                loadDocuments();
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to delete document');
            }
        } catch (error) {
            console.error('Error deleting document:', error);
            showMessage(`Error deleting document: ${error.message}`, 'error');
        }
    }

    window.showDeleteDocumentConfirmation = showDeleteDocumentConfirmation;
    window.deleteDocument = deleteDocument;

    loadDocuments();
});
