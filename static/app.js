/**
 * Grok Aurora Studio - Frontend
 * Handles UI interactions and WebSocket communication
 */

// State
let currentMode = 'image';
let ws = null;
let isGenerating = false;
let results = [];

// DOM Elements
const modeButtons = document.querySelectorAll('.mode-btn');
const generateBtn = document.getElementById('generateBtn');
const clearBtn = document.getElementById('clearBtn');
const promptInput = document.getElementById('prompt');
const charCount = document.getElementById('charCount');
const resultsList = document.getElementById('resultsList');
const loadingOverlay = document.getElementById('loadingOverlay');
const loadingText = document.getElementById('loadingText');
const statusPanel = document.getElementById('statusPanel');
const statusMessage = document.getElementById('statusMessage');
const authStatus = document.getElementById('authStatus');
const statusText = document.getElementById('statusText');

// Image controls
const imageControls = document.getElementById('imageControls');
const aspectRatio = document.getElementById('aspectRatio');
const quality = document.getElementById('quality');

// Video controls
const videoControls = document.getElementById('videoControls');
const duration = document.getElementById('duration');
const videoDimensionRatio = document.getElementById('videoDimensionRatio');
const resolution = document.getElementById('resolution');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    checkAuthStatus();
    setupCookieBridge();
});

function initializeEventListeners() {
    // Mode selection
    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            modeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMode = btn.dataset.mode;
            updateControlsVisibility();
        });
    });

    // Generate button
    generateBtn.addEventListener('click', handleGenerate);

    // Clear button
    clearBtn.addEventListener('click', () => {
        results = [];
        resultsList.innerHTML = '<div class="empty-state"><p>👈 Enter a prompt and click Generate to start</p></div>';
        clearBtn.style.display = 'none';
    });

    // Prompt input
    promptInput.addEventListener('input', (e) => {
        charCount.textContent = e.target.value.length;
    });
}

function updateControlsVisibility() {
    if (currentMode === 'image') {
        imageControls.style.display = 'flex';
        videoControls.style.display = 'none';
    } else {
        imageControls.style.display = 'none';
        videoControls.style.display = 'flex';
    }
}

async function checkAuthStatus() {
    try {
        const response = await fetch('/api/cookies');
        const data = await response.json();
        
        if (data.loaded) {
            setAuthStatus('ready', 'Ready to generate');
        } else {
            setAuthStatus('error', 'Cookies not loaded');
        }
    } catch (error) {
        setAuthStatus('error', 'Connection error');
    }
}

function setAuthStatus(status, text) {
    authStatus.className = `status-indicator ${status}`;
    statusText.textContent = text;
}

function setupCookieBridge() {
    // Create a hidden iframe to communicate with Grok
    const bridgeScript = `
    (function() {
        // Extract cookies from Grok website
        const extractCookies = () => {
            const cookies = {};
            document.cookie.split(';').forEach(c => {
                const [name, value] = c.trim().split('=');
                if (name) cookies[name] = value;
            });
            return cookies;
        };

        // Send cookies to parent window
        window.parent.postMessage({
            type: 'grok-cookies',
            cookies: extractCookies()
        }, '*');

        // Listen for requests from parent
        window.addEventListener('message', (e) => {
            if (e.data.type === 'get-cookies') {
                window.parent.postMessage({
                    type: 'grok-cookies',
                    cookies: extractCookies()
                }, '*');
            }
        });
    })();
    `;

    // Listen for cookie messages
    window.addEventListener('message', async (e) => {
        if (e.data.type === 'grok-cookies' && e.data.cookies) {
            try {
                const response = await fetch('/api/cookies', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cookies: e.data.cookies })
                });
                if (response.ok) {
                    checkAuthStatus();
                }
            } catch (error) {
                console.error('Failed to send cookies:', error);
            }
        }
    });

    // Try to extract cookies from current page if on Grok
    if (window.location.hostname.includes('grok')) {
        const cookies = {};
        document.cookie.split(';').forEach(c => {
            const [name, value] = c.trim().split('=');
            if (name) cookies[name] = value;
        });
        
        if (Object.keys(cookies).length > 0) {
            fetch('/api/cookies', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cookies })
            }).then(() => checkAuthStatus());
        }
    }
}

async function handleGenerate() {
    const prompt = promptInput.value.trim();
    
    if (!prompt) {
        showStatus('Please enter a prompt', 'error');
        return;
    }

    if (isGenerating) {
        showStatus('Already generating...', 'warning');
        return;
    }

    isGenerating = true;
    generateBtn.disabled = true;
    showLoading(true);
    clearStatus();

    try {
        if (currentMode === 'image') {
            await generateImage(prompt);
        } else {
            await generateVideo(prompt);
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        isGenerating = false;
        generateBtn.disabled = false;
        showLoading(false);
    }
}

async function generateImage(prompt) {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/generate-image`;
    
    return new Promise((resolve, reject) => {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            loadingText.textContent = 'Generating image...';
            ws.send(JSON.stringify({
                prompt,
                aspect_ratio: aspectRatio.value,
                quality: quality.value
            }));
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                if (data.status === 'error') {
                    showStatus(data.message, 'error');
                    reject(new Error(data.message));
                } else if (data.status === 'generating') {
                    updateStatus(JSON.stringify(data.data, null, 2));
                    
                    // Check if we have a result
                    if (data.data.content && data.data.content.includes('image')) {
                        addResult({
                            type: 'image',
                            prompt,
                            data: data.data,
                            timestamp: new Date().toLocaleString()
                        });
                    }
                }
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        };

        ws.onerror = (error) => {
            showStatus('WebSocket error', 'error');
            reject(error);
        };

        ws.onclose = () => {
            resolve();
        };
    });
}

async function generateVideo(prompt) {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/generate-video`;
    
    return new Promise((resolve, reject) => {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            loadingText.textContent = 'Generating video...';
            ws.send(JSON.stringify({
                prompt,
                duration: parseInt(duration.value),
                aspect_ratio: videoDimensionRatio.value,
                resolution: resolution.value
            }));
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                if (data.status === 'error') {
                    showStatus(data.message, 'error');
                    reject(new Error(data.message));
                } else if (data.status === 'generating') {
                    updateStatus(JSON.stringify(data.data, null, 2));
                    
                    // Check if we have a result
                    if (data.data.content && data.data.content.includes('video')) {
                        addResult({
                            type: 'video',
                            prompt,
                            data: data.data,
                            timestamp: new Date().toLocaleString()
                        });
                    }
                }
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        };

        ws.onerror = (error) => {
            showStatus('WebSocket error', 'error');
            reject(error);
        };

        ws.onclose = () => {
            resolve();
        };
    });
}

function addResult(result) {
    results.unshift(result);
    renderResults();
    clearBtn.style.display = 'inline-block';
}

function renderResults() {
    if (results.length === 0) {
        resultsList.innerHTML = '<div class="empty-state"><p>👈 Enter a prompt and click Generate to start</p></div>';
        return;
    }

    resultsList.innerHTML = results.map((result, index) => `
        <div class="result-item">
            <div class="result-thumbnail" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; color: white; font-size: 12px;">
                ${result.type === 'image' ? '🖼️ Image' : '🎬 Video'}
            </div>
            <div class="result-info">
                <div class="result-prompt">${result.prompt}</div>
                <small style="color: #95a5a6;">${result.timestamp}</small>
                <div class="result-actions">
                    <button class="download-btn" onclick="downloadResult(${index})">Download</button>
                    <button class="delete-btn" onclick="deleteResult(${index})">Delete</button>
                </div>
            </div>
        </div>
    `).join('');
}

function deleteResult(index) {
    results.splice(index, 1);
    renderResults();
    if (results.length === 0) {
        clearBtn.style.display = 'none';
    }
}

function downloadResult(index) {
    const result = results[index];
    const dataStr = JSON.stringify(result, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${result.type}-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
}

function showLoading(show) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
}

function showStatus(message, type = 'info') {
    statusPanel.style.display = 'block';
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
}

function updateStatus(message) {
    statusPanel.style.display = 'block';
    statusMessage.textContent = message;
    statusMessage.className = 'status-message';
}

function clearStatus() {
    statusPanel.style.display = 'none';
    statusMessage.textContent = '';
}

// Make functions globally available
window.deleteResult = deleteResult;
window.downloadResult = downloadResult;
