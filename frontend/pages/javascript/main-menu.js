// ============================================================================
// AUDIO SETUP
// ============================================================================
console.log('=== SCRIPT START: main-menu.js ===');

let masterVol = 0.5;
let musicVol = 0.5;
let sfxVol = 0.5;

const music = document.getElementById('menuMusic');
const clickOn = document.getElementById('menuClickOn');
const clickOff = document.getElementById('menuClickOff');

console.log('Audio elements:', { music, clickOn, clickOff });

// Start background music and set default volumes on first user interaction
function startMusic() {
  if (music.paused) {
    music.volume = musicVol*masterVol;
    music.play().catch(err => console.log('Autoplay prevented:', err));
  }
  clickOn.volume = sfxVol *masterVol
  clickOff.volume = sfxVol *masterVol
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

let inMatchmakingQueue = false;
let pendingChallenges = {}; // Store incoming challenges

// Sample deck
const sampleDeck = [
    "forbidden_lands", "eye_for_an_eye", "summon_peon", "pawn_scout",
    "knight_headhunter", "bishop_warlock",
    "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
    "knight_headhunter", "bishop_warlock",
    "forbidden_lands", "eye_for_an_eye", "summon_peon", "pawn_scout"
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
        
        // Display player ID in UI
        displayPlayerId();
        
        // Connect WebSocket
        connectWebSocket();
    } catch (error) {
        console.error('Failed to initialize player:', error);
        // Fallback to generating ID client-side if server is unavailable
        playerId = `player_${Math.random().toString(36).substr(2, 9)}`;
        console.log('Using fallback player ID:', playerId);
        displayPlayerId();
        connectWebSocket();
    }
}

function displayPlayerId() {
    const display = document.getElementById('playerIdDisplay');
    if (display && playerId) {
        display.textContent = `Player ID: ${playerId}`;
        display.style.display = 'block';
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
            inMatchmakingQueue = true;
            showStatus('Searching for opponent...');
            break;
            
        case 'game_started':
            gameId = data.game_id;
            playerColor = data.game_state.your_color;
            console.log(`Game started! ID: ${gameId}, Color: ${playerColor}`);
            
            inMatchmakingQueue = false;
            
            // Redirect to game page
            window.location.href = `/frontend/pages/html/game.html?game_id=${gameId}&player_id=${playerId}`;
            break;
            
        case 'challenge_received':
            console.log('Challenge received from:', data.challenger_id);
            handleChallengeReceived(data);
            break;
            
        case 'challenge_accepted':
            console.log('Challenge accepted by:', data.accepter_id);
            showStatus('Challenge accepted! Starting game...');
            break;
            
        case 'challenge_declined':
            console.log('Challenge declined by:', data.decliner_id);
            showStatus('Challenge was declined', true);
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
        name: playerId,
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

function sendChallenge() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showStatus('Connection error. Please refresh.', true);
        return;
    }
    
    // Remove from queue if in it
    if (inMatchmakingQueue) {
        removeFromQueue();
    }
    
    // Prompt for player ID
    const targetPlayerId = prompt('Enter the Player ID of the opponent you want to challenge:');
    
    if (!targetPlayerId || targetPlayerId.trim() === '') {
        console.log('Challenge cancelled - no ID entered');
        return;
    }
    
    if (targetPlayerId.trim() === playerId) {
        showStatus('You cannot challenge yourself!', true);
        return;
    }
    
    console.log('Sending challenge to:', targetPlayerId);
    
    const message = {
        type: 'send_challenge',
        target_player_id: targetPlayerId.trim(),
        challenger_name: playerId,
        deck: sampleDeck
    };
    
    ws.send(JSON.stringify(message));
    showStatus(`Challenge sent to ${targetPlayerId}...`);
}

function removeFromQueue() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        return;
    }
    
    console.log('Removing from matchmaking queue');
    
    const message = {
        type: 'leave_queue'
    };
    
    ws.send(JSON.stringify(message));
    inMatchmakingQueue = false;
}

function handleChallengeReceived(data) {
    const challengerId = data.challenger_id;
    const challengerName = data.challenger_name || challengerId;
    
    // Store the challenge
    pendingChallenges[challengerId] = data;
    
    confirmChallenge(challengerId, challengerName);
}

function confirmChallenge(challengerId, challengerName) {
    console.log("Displaying challenge UI for:", challengerId);

    const acceptBtn = document.getElementById("acceptChallengeBtn");
    const declineBtn = document.getElementById("declineChallengeBtn");

    // Show the buttons
    acceptBtn.style.display = "block";
    declineBtn.style.display = "block";

    // Update text
    acceptBtn.textContent = `Accept ${challengerName}'s Challenge`;
    declineBtn.textContent = `Decline ${challengerName}'s Challenge`;

    // Clear previous handlers
    acceptBtn.replaceWith(acceptBtn.cloneNode(true));
    declineBtn.replaceWith(declineBtn.cloneNode(true));

    const newAccept = document.getElementById("acceptChallengeBtn");
    const newDecline = document.getElementById("declineChallengeBtn");

    // Attach new handlers
    newAccept.onclick = () => {
        hideChallengeButtons();
        acceptChallenge(challengerId);
    };

    newDecline.onclick = () => {
        hideChallengeButtons();
        declineChallenge(challengerId);
    };
}

function hideChallengeButtons() {
    document.getElementById("acceptChallengeBtn").style.display = "none";
    document.getElementById("declineChallengeBtn").style.display = "none";
}


function acceptChallenge(challengerId) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showStatus('Connection error. Please refresh.', true);
        return;
    }
    
    // Remove from queue if in it
    if (inMatchmakingQueue) {
        removeFromQueue();
    }
    
    console.log('Accepting challenge from:', challengerId);
    
    const challenge = pendingChallenges[challengerId];
    
    const message = {
        type: 'accept_challenge',
        challenger_id: challengerId,
        accepter_name: playerId,
        deck: sampleDeck
    };
    
    ws.send(JSON.stringify(message));
    delete pendingChallenges[challengerId];
    
    showStatus('Accepting challenge...');
}

function declineChallenge(challengerId) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        return;
    }
    
    console.log('Declining challenge from:', challengerId);
    
    const message = {
        type: 'decline_challenge',
        challenger_id: challengerId
    };
    
    ws.send(JSON.stringify(message));
    delete pendingChallenges[challengerId];
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
    sendChallenge();
});

document.getElementById('tutorial').addEventListener('click', () => {
    console.log('Tutorial clicked');
    // Redirect to tutorial page
    window.location.href = '/frontend/pages/html/tutorial.html';
});

document.getElementById('credits').addEventListener('click', () => {
    console.log('Credits clicked');
    
    window.location.href = '/frontend/pages/html/credits.html';
});

document.getElementById('settings').addEventListener('click', () => {
    console.log('Settings clicked');
    document.getElementById("options-backdrop").style.display = "flex";
});

document.getElementById('exit').addEventListener('click', () => {
    console.log('Exit clicked');
    // Closes the window
    if (confirm('Are you sure you want to exit?')) {
        window.close();
    }
});

document.getElementById('save').addEventListener('click', () => {
    //Add logic to check slider elements for their values

    masterVol = (master_vol_slider.value/100);
    musicVol = (music_vol_slider.value/100);
    sfxVol = (sfx_vol_slider.value/100);

    music.volume = musicVol*masterVol;
    clickOff.volume = sfxVol*masterVol;
    clickOn.volume = sfxVol*masterVol;

    document.getElementById("options-backdrop").style.display = "none";
    console.log('Options saved');
});

document.getElementById('back').addEventListener('click', () => {
    document.getElementById("options-backdrop").style.display = "none";
    music.volume = musicVol*masterVol
    clickOff.volume = sfxVol*masterVol
    clickOn.volume = sfxVol*masterVol
    master_vol_slider.value = masterVol*100;
    music_vol_slider.value = musicVol*100;
    sfx_vol_slider.value = sfxVol*100;
    console.log('Options closed');
});

// ============================================================================
// Slider Setup
// ============================================================================
const master_vol_slider = document.getElementById('master_volume');
master_vol_slider.addEventListener('input', ()=>{
    music.volume = (music_vol_slider.value/100)*(master_vol_slider.value/100)
    clickOn.volume = (sfx_vol_slider.value / 100)*(master_vol_slider.value/100);
    clickOff.volume = (sfx_vol_slider.value / 100)*(master_vol_slider.value/100);
    console.log("Master Volume: " + master_vol_slider.value/100)
});

const music_vol_slider = document.getElementById('music_volume');
music_vol_slider.addEventListener('input', ()=>{
    music.volume = (music_vol_slider.value/100)*(master_vol_slider.value/100);
    console.log("Music Volume: " + music_vol_slider.value/100)
});

const sfx_vol_slider = document.getElementById('sfx_volume');
sfx_vol_slider.addEventListener('input', ()=>{
    const volume = (sfx_vol_slider.value / 100)*(master_vol_slider.value/100);
    console.log("SFX Volume: " + sfx_vol_slider.value/100)
    clickOn.volume = volume;
    clickOff.volume = volume;
    
    // Play a test sound so user can hear the change
    clickOn.currentTime = 0; // Reset to start in case it's already playing
    clickOn.play();
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