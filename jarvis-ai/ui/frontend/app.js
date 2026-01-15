/**
 * JARVIS UI - Main Application
 * 
 * Handles WebSocket connection, command execution, and UI updates.
 */

class JarvisApp {
    constructor() {
        this.apiEndpoint = localStorage.getItem('apiEndpoint') || 'http://localhost:8080';
        this.wsEndpoint = this.apiEndpoint.replace('http', 'ws') + '/ws';
        this.ws = null;
        this.connected = false;
        this.history = JSON.parse(localStorage.getItem('commandHistory') || '[]');
        
        this.init();
    }
    
    init() {
        // DOM elements
        this.elements = {
            messagesContainer: document.getElementById('messages'),
            commandInput: document.getElementById('command-input'),
            sendBtn: document.getElementById('send-btn'),
            voiceBtn: document.getElementById('voice-btn'),
            connectionStatus: document.getElementById('connection-status'),
            toolsGrid: document.getElementById('tools-grid'),
            toolsSearch: document.getElementById('tools-search'),
            historyList: document.getElementById('history-list'),
            clearHistory: document.getElementById('clear-history'),
            apiEndpointInput: document.getElementById('api-endpoint'),
        };
        
        // Event listeners
        this.setupEventListeners();
        
        // Navigation
        this.setupNavigation();
        
        // Connect to API
        this.connect();
        
        // Load tools
        this.loadTools();
        
        // Render history
        this.renderHistory();
        
        // Load settings
        this.loadSettings();
    }
    
    setupEventListeners() {
        // Send command
        this.elements.sendBtn.addEventListener('click', () => this.sendCommand());
        this.elements.commandInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendCommand();
            }
        });
        
        // Voice input
        this.elements.voiceBtn.addEventListener('click', () => this.toggleVoice());
        
        // Tools search
        this.elements.toolsSearch.addEventListener('input', (e) => this.filterTools(e.target.value));
        
        // Clear history
        this.elements.clearHistory.addEventListener('click', () => this.clearHistory());
        
        // API endpoint change
        this.elements.apiEndpointInput.addEventListener('change', (e) => {
            this.apiEndpoint = e.target.value;
            localStorage.setItem('apiEndpoint', this.apiEndpoint);
            this.wsEndpoint = this.apiEndpoint.replace('http', 'ws') + '/ws';
            this.connect();
        });
        
        // Settings checkboxes
        document.querySelectorAll('.setting-item input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.saveSettings());
        });
    }
    
    setupNavigation() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const view = item.dataset.view;
                
                // Update nav
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                item.classList.add('active');
                
                // Update view
                document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
                document.getElementById(`view-${view}`).classList.add('active');
            });
        });
    }
    
    connect() {
        if (this.ws) {
            this.ws.close();
        }
        
        try {
            this.ws = new WebSocket(this.wsEndpoint);
            
            this.ws.onopen = () => {
                this.connected = true;
                this.updateConnectionStatus(true);
                console.log('Connected to JARVIS');
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            };
            
            this.ws.onclose = () => {
                this.connected = false;
                this.updateConnectionStatus(false);
                console.log('Disconnected from JARVIS');
                
                // Reconnect after delay
                setTimeout(() => this.connect(), 5000);
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('Connection failed:', error);
            this.updateConnectionStatus(false);
        }
    }
    
    updateConnectionStatus(connected) {
        const status = this.elements.connectionStatus;
        if (connected) {
            status.classList.add('connected');
            status.querySelector('span:last-child').textContent = 'Connected';
        } else {
            status.classList.remove('connected');
            status.querySelector('span:last-child').textContent = 'Disconnected';
        }
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'connected':
                console.log('WebSocket connected:', data.message);
                break;
                
            case 'result':
                this.addMessage('assistant', this.formatResult(data.result, data.success));
                break;
                
            case 'command_result':
                // Broadcast from another client
                break;
                
            case 'pong':
                // Keepalive response
                break;
        }
    }
    
    async sendCommand() {
        const command = this.elements.commandInput.value.trim();
        if (!command) return;
        
        // Add user message
        this.addMessage('user', command);
        this.elements.commandInput.value = '';
        
        // Add to history
        this.addToHistory(command);
        
        if (this.connected) {
            // Send via WebSocket
            this.ws.send(JSON.stringify({
                type: 'command',
                command: command,
            }));
        } else {
            // Fallback to REST API
            try {
                const response = await fetch(`${this.apiEndpoint}/command`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command }),
                });
                
                const data = await response.json();
                this.addMessage('assistant', this.formatResult(data.result, data.success));
            } catch (error) {
                this.addMessage('assistant', `Error: Unable to reach JARVIS server. ${error.message}`);
            }
        }
    }
    
    formatResult(result, success) {
        if (!success) {
            return `❌ Error: ${result || 'Command failed'}`;
        }
        
        if (typeof result === 'object') {
            return `<pre>${JSON.stringify(result, null, 2)}</pre>`;
        }
        
        return result || '✓ Command executed successfully';
    }
    
    addMessage(role, content) {
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        const message = document.createElement('div');
        message.className = `message ${role}`;
        message.innerHTML = `
            <div class="message-avatar">${role === 'user' ? 'U' : 'J'}</div>
            <div class="message-content">
                <p>${content}</p>
                <span class="message-time">${time}</span>
            </div>
        `;
        
        this.elements.messagesContainer.appendChild(message);
        this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
    }
    
    async loadTools() {
        try {
            const response = await fetch(`${this.apiEndpoint}/tools`);
            const data = await response.json();
            
            this.tools = data.tools || [];
            this.renderTools(this.tools);
        } catch (error) {
            console.error('Failed to load tools:', error);
            this.elements.toolsGrid.innerHTML = '<p>Unable to load tools. Is the server running?</p>';
        }
    }
    
    renderTools(tools) {
        this.elements.toolsGrid.innerHTML = tools.map(tool => `
            <div class="tool-card" data-tool="${tool.name}">
                <h3>${tool.name}</h3>
                <p>${tool.description}</p>
                <span class="category">${tool.category}</span>
            </div>
        `).join('');
        
        // Click to use tool
        document.querySelectorAll('.tool-card').forEach(card => {
            card.addEventListener('click', () => {
                const toolName = card.dataset.tool;
                this.elements.commandInput.value = toolName + ' ';
                this.elements.commandInput.focus();
                
                // Switch to chat view
                document.querySelector('.nav-item[data-view="chat"]').click();
            });
        });
    }
    
    filterTools(query) {
        const filtered = this.tools.filter(tool =>
            tool.name.toLowerCase().includes(query.toLowerCase()) ||
            tool.description.toLowerCase().includes(query.toLowerCase()) ||
            tool.category.toLowerCase().includes(query.toLowerCase())
        );
        this.renderTools(filtered);
    }
    
    addToHistory(command) {
        this.history.unshift({
            command,
            timestamp: Date.now(),
        });
        
        // Limit history
        this.history = this.history.slice(0, 100);
        localStorage.setItem('commandHistory', JSON.stringify(this.history));
        
        this.renderHistory();
    }
    
    renderHistory() {
        this.elements.historyList.innerHTML = this.history.map((item, index) => {
            const date = new Date(item.timestamp).toLocaleString();
            return `
                <div class="history-item" data-index="${index}">
                    <span>${item.command}</span>
                    <span>${date}</span>
                </div>
            `;
        }).join('');
        
        // Click to reuse
        document.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                this.elements.commandInput.value = this.history[index].command;
                this.elements.commandInput.focus();
                document.querySelector('.nav-item[data-view="chat"]').click();
            });
        });
    }
    
    clearHistory() {
        this.history = [];
        localStorage.removeItem('commandHistory');
        this.renderHistory();
    }
    
    toggleVoice() {
        const voiceEnabled = document.getElementById('voice-enabled').checked;
        if (!voiceEnabled) return;
        
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert('Voice recognition is not supported in this browser.');
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        
        this.elements.voiceBtn.classList.add('recording');
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            this.elements.commandInput.value = transcript;
            this.elements.voiceBtn.classList.remove('recording');
        };
        
        recognition.onerror = () => {
            this.elements.voiceBtn.classList.remove('recording');
        };
        
        recognition.onend = () => {
            this.elements.voiceBtn.classList.remove('recording');
        };
        
        recognition.start();
    }
    
    loadSettings() {
        const settings = JSON.parse(localStorage.getItem('jarvisSettings') || '{}');
        
        if (settings.voiceEnabled !== undefined) {
            document.getElementById('voice-enabled').checked = settings.voiceEnabled;
        }
        if (settings.ttsEnabled !== undefined) {
            document.getElementById('tts-enabled').checked = settings.ttsEnabled;
        }
        if (settings.darkMode !== undefined) {
            document.getElementById('dark-mode').checked = settings.darkMode;
        }
        
        this.elements.apiEndpointInput.value = this.apiEndpoint;
    }
    
    saveSettings() {
        const settings = {
            voiceEnabled: document.getElementById('voice-enabled').checked,
            ttsEnabled: document.getElementById('tts-enabled').checked,
            darkMode: document.getElementById('dark-mode').checked,
        };
        localStorage.setItem('jarvisSettings', JSON.stringify(settings));
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    window.jarvis = new JarvisApp();
});
