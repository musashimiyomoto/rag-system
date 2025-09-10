document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const sessionsList = document.getElementById('sessions-list');
    const newSessionBtn = document.getElementById('new-session-btn');
    const modelSelect = document.getElementById('model-select');
    const backBtn = document.getElementById('back-btn');
    const deleteSessionBtn = document.getElementById('delete-session-btn');
    const documentTitle = document.getElementById('document-title');

    loadDocumentInfo();
    loadSessions();

    newSessionBtn.addEventListener('click', createNewSession);
    backBtn.addEventListener('click', () => {
        window.location.href = '/';
    });
    deleteSessionBtn.addEventListener('click', showDeleteConfirmation);

    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        if (!currentSessionId) {
            await createNewSession();
        }

        const message = messageInput.value.trim();
        if (!message) return;

        addMessage(message, 'user');
        messageInput.value = '';

        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message agent loading-message';
        loadingDiv.innerHTML = '<div>Thinking...</div>';
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const selectedModel = modelSelect.value;
            const response = await fetch(`/chat/stream?llm=${encodeURIComponent(selectedModel)}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: currentSessionId
                })
            });

            if (!response.ok) {
                throw new Error('Failed to send message');
            }

            loadingDiv.remove();

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let agentMessageDiv = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n').filter(line => line.trim());

                for (const line of lines) {
                    try {
                        const data = JSON.parse(line);
                        if (data.role === 'agent' && data.content) {
                            if (!agentMessageDiv) {
                                agentMessageDiv = document.createElement('div');
                                agentMessageDiv.className = 'message agent';
                                chatMessages.appendChild(agentMessageDiv);
                            }

                            let time;
                            try {
                                time = new Date(data.timestamp);
                                if (isNaN(time.getTime()) || time.getFullYear() < 2020) {
                                    time = new Date();
                                }
                            } catch (e) {
                                time = new Date();
                            }
                            const timeString = time.toLocaleTimeString();

                            agentMessageDiv.innerHTML = `
                                <div>${data.content}</div>
                                <div class="message-time">${timeString}</div>
                            `;

                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }
                    } catch (e) {
                        console.error('Error parsing chunk:', e);
                    }
                }
            }
        } catch (error) {
            loadingDiv.remove();
            addMessage('Error: ' + error.message, 'agent', true);
        }
    });

    async function loadSessions() {
        try {
            const response = await fetch(`/document/${documentId}/session/list`);
            const sessions = await response.json();

            if (sessions.length === 0) {
                sessionsList.innerHTML = '<div class="loading">No sessions yet</div>';
                return;
            }

            sessionsList.innerHTML = sessions.map(session => `
                <div class="session-item" onclick="loadSession(${session.id})">
                    <div class="session-id">Session ${session.id}</div>
                    <div class="session-date">${new Date(session.created_at).toLocaleString()}</div>
                </div>
            `).join('');
        } catch (error) {
            sessionsList.innerHTML = '<div class="error">Failed to load sessions</div>';
        }
    }

    async function createNewSession() {
        try {
            const response = await fetch('/session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    document_id: documentId
                })
            });

            if (response.ok) {
                const session = await response.json();
                currentSessionId = session.id;
                chatMessages.innerHTML = '<div class="welcome-message"><p>New session started. Ask questions about your document.</p></div>';
                loadSessions();
                updateSessionUI();
            } else {
                throw new Error('Failed to create session');
            }
        } catch (error) {
            addMessage('Error creating session: ' + error.message, 'agent', true);
        }
    }

    window.loadSession = async function(sessionId) {
        currentSessionId = sessionId;

        try {
            const response = await fetch(`/session/${sessionId}/message/list`);
            const messages = await response.json();

            chatMessages.innerHTML = '';
            messages.forEach(msg => {
                addMessage(msg.content, msg.role, false, msg.timestamp);
            });

            updateSessionUI();
        } catch (error) {
            addMessage('Error loading session: ' + error.message, 'agent', true);
        }
    };

    function addMessage(content, role, isError = false, timestamp = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        if (isError) {
            messageDiv.style.backgroundColor = '#f8d7da';
            messageDiv.style.color = '#721c24';
        }

        const time = timestamp ? new Date(timestamp) : new Date();
        const timeString = time.toLocaleTimeString();

        messageDiv.innerHTML = `
            <div>${content}</div>
            <div class="message-time">${timeString}</div>
        `;

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }


    function updateSessionUI() {
        const sessionItems = document.querySelectorAll('.session-item');
        sessionItems.forEach(item => {
            item.classList.remove('active');
            if (item.textContent.includes(`Session ${currentSessionId}`)) {
                item.classList.add('active');
            }
        });

        if (currentSessionId) {
            deleteSessionBtn.style.display = 'flex';
        } else {
            deleteSessionBtn.style.display = 'none';
        }
    }

    async function loadDocumentInfo() {
        try {
            const response = await fetch(`/document/${documentId}`);
            const document = await response.json();

            if (document.summary) {
                const maxLength = 60;
                const truncatedSummary = document.summary.length > maxLength
                    ? document.summary.substring(0, maxLength) + "..."
                    : document.summary;
                documentTitle.textContent = truncatedSummary;
            } else {
                documentTitle.textContent = `Document ${documentId}`;
            }
        } catch (error) {
            console.error('Error loading document info:', error);
            documentTitle.textContent = `Document ${documentId}`;
        }
    }

    function showDeleteConfirmation() {
        if (!currentSessionId) return;

        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Delete Session</h3>
                    <button class="close-btn" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <p>Are you sure you want to delete the current session? This action cannot be undone.</p>
                </div>
                <div class="modal-footer">
                    <button class="cancel-delete-btn" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                    <button class="confirm-delete-btn" onclick="deleteCurrentSession()">Delete</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    async function deleteCurrentSession() {
        if (!currentSessionId) return;

        try {
            const response = await fetch(`/session/${currentSessionId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                const modal = document.querySelector('.modal-overlay');
                if (modal) modal.remove();

                currentSessionId = null;
                deleteSessionBtn.style.display = 'none';

                chatMessages.innerHTML = '<div class="welcome-message"><p>Start a conversation with your document. Ask questions about its content.</p></div>';

                loadSessions();

                addMessage('Session deleted successfully', 'agent');
            } else {
                throw new Error('Failed to delete session');
            }
        } catch (error) {
            console.error('Error deleting session:', error);
            addMessage('Error deleting session: ' + error.message, 'agent', true);
        }
    }

    window.deleteCurrentSession = deleteCurrentSession;
});
