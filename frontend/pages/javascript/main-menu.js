// ============================================================================
// AUDIO SETUP
// ============================================================================
console.log('=== SCRIPT START: main-menu.js ===');

const music = document.getElementById('menuMusic');
const clickOn = document.getElementById('menuClickOn');
const clickOff = document.getElementById('menuClickOff');

console.log('Audio elements:', { music, clickOn, clickOff });

// Start background music on first user interaction
function startMusic() {
  if (music.paused) {
    music.volume = 0.3;
    music.play().catch(err => console.log('Autoplay prevented:', err));
  }
}
document.addEventListener('click', startMusic, { once: true });
document.addEventListener('keydown', startMusic, { once: true });

// ============================================================================
// NETWORKING SETUP
// ============================================================================
let ws = null;
let playerId = null;
let gameId = null;
let playerColor = null;

// Sample deck (16 cards matching your card registry)
const sampleDeck = [
    "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
    "knight_headhunter", "bishop_warlock",
    "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
    "knight_headhunter", "bishop_warlock",
    "mine", "eye_for_an_eye", "summon_peon", "pawn_scout"
];

// Get the server URL (adjust this based on your deployment)
const SERVER_URL = window.location.hostname === 'localhost' 
    ? 'localhost:8000'
    : window.location.host;

// Initialize connection on page load
async function initializePlayer() {
    console.log('initializePlayer() called');
    try {
        // Get a unique player ID from the server
        const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
        const url = `${protocol}//${SERVER_URL}/get_player_id`;
        console.log('Fetching player ID from:', url);
        
        const response = await fetch(url);
        const data = await response.json();
        playerId = data.player_id;
        console.log('✓ Assigned player ID:', playerId);
        
        // Connect WebSocket
        connectWebSocket();
    } catch (error) {
        console.error('Failed to initialize player:', error);
        // Fallback to generating ID client-side if server is unavailable
        playerId = `player_${Math.random().toString(36).substr(2, 9)}`;
        console.log('Using fallback player ID:', playerId);
        connectWebSocket();
    }
}

function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${SERVER_URL}/ws/${playerId}`;
    
    console.log('Connecting WebSocket to:', wsUrl);
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('✓ WebSocket Connected!');
        // Enable the quickplay button once connected
        const quickplayBtn = document.getElementById('quickplay');
        if (quickplayBtn) {
            quickplayBtn.disabled = false;
            console.log('✓ Quickplay button enabled');
        }
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('WebSocket received:', data);
        handleServerMessage(data);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        // Disable quickplay button when disconnected
        const quickplayBtn = document.getElementById('quickplay');
        if (quickplayBtn) {
            quickplayBtn.disabled = true;
        }
        
        // Attempt to reconnect after 3 seconds
        console.log('Will attempt reconnect in 3 seconds...');
        setTimeout(() => {
            console.log('Attempting to reconnect...');
            connectWebSocket();
        }, 3000);
    };
}

function handleServerMessage(data) {
    const msgType = data.type;
    console.log('Received:', msgType, data);
    
    switch(msgType) {
        case 'queue_joined':
            console.log('Joined matchmaking queue:', data.message);
            showStatus('Searching for opponent...');
            break;
            
        case 'game_started':
            gameId = data.game_id;
            playerColor = data.game_state.your_color;
            console.log(`Game started! ID: ${gameId}, Color: ${playerColor}`);
            
            // Redirect to game page
            // TODO: Update this URL to match your game page
            window.location.href = `/game.html?game_id=${gameId}&player_id=${playerId}`;
            break;
            
        case 'error':
            console.error('Server error:', data.message);
            showStatus(`Error: ${data.message}`, true);
            break;
            
        case 'pong':
            console.log('Pong received');
            break;
    }
}

function joinQueue() {
    console.log('joinQueue() called');
    console.log('WebSocket state:', ws ? ws.readyState : 'null');
    
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.error('Not connected to server! ws:', ws, 'readyState:', ws?.readyState);
        showStatus('Connection error. Please refresh.', true);
        return;
    }
    
    const message = { 
        type: 'join_queue',
        name: playerId, // Use player ID as name for now
        deck: sampleDeck
    };
    
    console.log('Sending join_queue message:', message);
    ws.send(JSON.stringify(message));
    console.log('✓ Message sent');
}

function showStatus(message, isError = false) {
    console.log(isError ? 'ERROR:' : 'STATUS:', message);
    
    // Show status message in UI
    const statusIndicator = document.getElementById('statusIndicator');
    const statusMessage = document.getElementById('statusMessage');
    
    if (statusIndicator && statusMessage) {
        statusMessage.textContent = message;
        statusMessage.style.color = isError ? '#ff4444' : '#44ff44';
        statusIndicator.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            statusIndicator.style.display = 'none';
        }, 5000);
    }
}

// ============================================================================
// BUTTON SETUP
// ============================================================================

// Apply sounds and functionality to each button
document.querySelectorAll('.menu-btn').forEach(btn => {
    // Play "click on" when pressing down
    btn.addEventListener('mousedown', () => {
        clickOn.currentTime = 0;
        clickOn.volume = 0.7;
        clickOn.play().catch(() => {});
    });

    // Play "click off" when releasing the mouse
    btn.addEventListener('mouseup', () => {
        clickOff.currentTime = 0;
        clickOff.volume = 0.7;
        clickOff.play().catch(() => {});
    });
});

// Button click handlers
document.getElementById('quickplay').addEventListener('click', () => {
    console.log('Quickplay clicked');
    joinQueue();
});

document.getElementById('directconnect').addEventListener('click', () => {
    console.log('Direct Connect clicked');
    // TODO: Implement direct connect functionality
    showStatus('Direct connect not yet implemented');
});

document.getElementById('tutorial').addEventListener('click', () => {
    console.log('Tutorial clicked');
    // Redirect to tutorial page
    window.location.href = '/frontend/pages/html/tutorial.html';
});

document.getElementById('credits').addEventListener('click', () => {
    console.log('Credits clicked');
    // TODO: Show credits modal or page
    showStatus('Credits not yet implemented');
});

document.getElementById('settings').addEventListener('click', () => {
    console.log('Settings clicked');
    // TODO: Show settings modal
    showStatus('Settings not yet implemented');
});

document.getElementById('exit').addEventListener('click', () => {
    console.log('Exit clicked');
    // For web app, this could close the tab or show a confirmation
    if (confirm('Are you sure you want to exit?')) {
        window.close();
    }
});

// ============================================================================
// INITIALIZATION
// ============================================================================

console.log('=== Arcane Chess Integration Script Loaded ===');

// Disable quickplay button until connected
// Wait for DOM to be ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

function init() {
    console.log('DOM Ready - Initializing...');
    const quickplayBtn = document.getElementById('quickplay');
    if (quickplayBtn) {
        quickplayBtn.disabled = true;
        console.log('Quickplay button found and disabled');
    } else {
        console.error('ERROR: Quickplay button not found!');
    }
    initializePlayer();
}

// Also try window.load as backup
window.addEventListener('load', () => {
    console.log('Window load event fired');
});