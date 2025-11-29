// ============================================================================
// WEBSOCKET & NETWORKING SETUP
// ============================================================================

// Global networking variables
let ws = null;
let gameId = null;
let playerId = null;
let playerColor = null;
let timerInterval = null;
let lastTimerUpdate = Date.now();
let pendingCardPlay = null;
let lastMoveSentAt = null;

// Get server URL
const SERVER_URL = window.location.hostname === 'localhost' 
    ? 'localhost:8000'
    : window.location.host;

// Parse URL parameters on page load
function parseURLParams() {
    const urlParams = new URLSearchParams(window.location.search);
    gameId = urlParams.get('game_id');
    playerId = urlParams.get('player_id');
    
    console.log('URL Parameters:', { gameId, playerId });
    
    if (!gameId || !playerId) {
        console.error('Missing game_id or player_id in URL');
        alert('Error: Missing game information. Please start a new game.');
        window.location.href = '/frontend/pages/html/main_menu.html';
        return false;
    }
    
    return true;
}

// Connect to game via WebSocket
function connectToGame() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${SERVER_URL}/ws/${playerId}`;
    
    console.log('Connecting to game server:', wsUrl);
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('✓ Connected to game server');
        // Request the current game state
        requestGameState();
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleGameMessage(data);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('Disconnected from game server');
        // Could add reconnection logic here
    };
}

// Request current game state from server
function requestGameState() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.error('WebSocket not connected');
        return;
    }
    
    const message = {
        type: 'get_game_state',
        game_id: gameId
    };

    ws.send(JSON.stringify(message));

    console.log('Requested game state for:', gameId);
}

// Handle incoming WebSocket messages
function handleGameMessage(data) {
    const msgType = data.type;
    console.log('Received message:', msgType, data);
    
    switch(msgType) {
        case 'game_state':
            // Initial game state received
            console.log('Game state received:', data.game_state);
            updateGameState(data.game_state);
            
            // Check if card play succeeded
            if (pendingCardPlay) {
                const me = gameState.players.find(p => p.color === playerColor);
                const cardStillInHand = me && me.hand.includes(pendingCardPlay.cardId);
                
                if (!cardStillInHand) {
                    // Card was played successfully! Update UI
                    const { cardData, cardElement } = pendingCardPlay;
                    
                    if (cardElement) {
                        animateCardToDiscard(cardElement, cardData, () => {
                            showCardOverlay(`Played: ${cardData.name}`);
                        });
                    }
                    
                    // Re-render hands to reflect server state
                    renderHands();
                    
                    // Clear pending
                    pendingCardPlay = null;
                }
            }
            break;
            
        case 'game_update':
            // Game state changed (someone made a move)
            console.log('Game updated:', data.action);
            updateGameState(data.game_state);

            // If opponent played a card, show animation
            if (data.action === 'play_card' && data.card_played && !data.game_state.your_turn) {
                handleOpponentCardPlay(data.card_played);
            }
            // IBK added timing report
            reportMoveTiming();
            
            // Check if our card play succeeded
            if (pendingCardPlay) {
                const me = gameState.players.find(p => p.color === playerColor);
                const cardStillInHand = me && me.hand.includes(pendingCardPlay.cardId);
                
                if (!cardStillInHand) {
                    // Card was played successfully! Update UI
                    const { cardData, cardElement } = pendingCardPlay;
                    
                    if (cardElement) {
                        animateCardToDiscard(cardElement, cardData, () => {
                            showCardOverlay(`Played: ${cardData.name}`);
                        });
                    }
                    
                    // Re-render hands to reflect server state
                    renderHands();
                    
                    // Clear pending
                    pendingCardPlay = null;
                }
            }
            break;
            
        case 'game_over':
            console.log('Game over:', data.reason, 'Winner:', data.winner);
            handleGameOver(data);
            break;
            
        case 'error':
            console.error('Server error:', data.message);
            alert('Error: ' + data.message);
            
            // Card play failed clear pending but DON'T update UI
            if (pendingCardPlay) {
                console.log('Card play failed, keeping card in hand');
                pendingCardPlay = null;
            }
            break;
            
        default:
            console.log('Unknown message type:', msgType);
    }
}

// Update local game state with server data
function updateGameState(serverGameState) {
    console.log('Updating game state:', serverGameState);
    console.log('=== updateGameState called ===');
    console.log('Server game state:', JSON.stringify(serverGameState, null, 2));
    console.log('Your color:', serverGameState.your_color);
    console.log('Your turn:', serverGameState.your_turn);
    console.log('Board pieces count:', serverGameState.board?.pieces?.length || 0);
    
    // Update player color if we don't have it yet
    if (!playerColor && serverGameState.your_color) {
    playerColor = serverGameState.your_color;
    console.log('Player color set to:', playerColor);
    }
    
    // Convert server format to our local gameState format
    // The server sends a player-specific view, we need to reconstruct the full state
    gameState.game_id = gameId;
    gameState.dmz = serverGameState.board?.dmz_active || false;
    
    // Update board pieces
    if (serverGameState.board && serverGameState.board.pieces) {
        gameState.board = serverGameState.board.pieces.map(piece => ({
            id: piece.id,
            type: piece.type,
            color: piece.color,
            position: piece.position_algebraic,
            status: piece.status || 'active',
            moves: piece.moves || []
        }));
    }
    
    // Update player data (reconstruct both players from server view)
    if (!gameState.players || gameState.players.length === 0) {
        gameState.players = [
            {
                player_id: playerId,
                name: 'You',
                color: serverGameState.your_color,
                hand: serverGameState.your_hand || [],
                deck_size: serverGameState.your_deck_size || 0,
                captured_pieces: []
            },
            {
                player_id: 'opponent',
                name: 'Opponent',
                color: serverGameState.your_color === 'w' ? 'b' : 'w',
                hand: [], // We don't see opponent's hand
                hand_size: serverGameState.opponent_hand_size || 0,
                deck_size: serverGameState.opponent_deck_size || 0,
                captured_pieces: []
            }
        ];
    } else {
        // Update existing player data
        gameState.players[0].hand = serverGameState.your_hand || [];
        gameState.players[0].deck_size = serverGameState.your_deck_size || 0;
        gameState.players[1].hand_size = serverGameState.opponent_hand_size || 0;
        gameState.players[1].deck_size = serverGameState.opponent_deck_size || 0;
    }
    
    // Update turn information
    gameState.current_turn = serverGameState.current_turn;
    gameState.your_turn = serverGameState.your_turn;
    
    // Update timers
    gameState.white_time = serverGameState.white_time;
    gameState.black_time = serverGameState.black_time;
    
    // Store special tiles if present
    if (serverGameState.board) {
        gameState.greenTiles = serverGameState.board.greenTiles || [];
        gameState.forbiddenTiles = serverGameState.board.forbiddenTiles || [];
        gameState.mines = serverGameState.board.mines || [];
        gameState.glueTiles = serverGameState.board.glueTiles || [];
    }
    
    console.log('Game state updated:', gameState);
    
    // Update the UI with new state
    updateFullUI();
}

// Send a move to the server
function sendMove(fromSquare, toSquare) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.error('Cannot send move: not connected');
        return;
    }
    
    if (!gameState.your_turn) {
        console.log('Not your turn!');
        return;
    }
    
    // RECORD TIME MOVE WAS SENT
    lastMoveSentAt = performance.now();

    const message = {
        type: 'make_move',
        game_id: gameId,
        from: fromSquare,
        to: toSquare
    };
    
    console.log('Sending move:', message);
    ws.send(JSON.stringify(message));
}

function sendPlayCard(cardId, targetData = {}, cardElement = null, cardData = null) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.error('Cannot play card: not connected');
        return;
    }
    
    if (!gameState.your_turn) {
        console.log('Not your turn!');
        return;
    }
    
    // Get card data if not provided
    if (!cardData) {
        cardData = getCardData(cardId);
    }
    
    // Store pending card info for when we get server response
    pendingCardPlay = {
        cardId: cardId,
        cardData: cardData,
        cardElement: cardElement,
        targetData: targetData
    };
    
    const message = {
        type: 'play_card',
        game_id: gameId,
        card_id: cardId,
        target: targetData
    };
    
    console.log('=== Sending card play ===');
    console.log('Card ID:', cardId);
    console.log('Target data:', targetData);
    console.log('Full message:', JSON.stringify(message, null, 2));
    
    ws.send(JSON.stringify(message));
}
// Handle game over
function handleGameOver(data) {
    alert(`Game Over!\nReason: ${data.reason}\nWinner: ${data.winner || 'Draw'}`);
    // Could add a game over screen here
}


// gamestate json populated by server
const gameState = {
    board: [],
    players: [],
    dmz: false,
    logs: []
};

// ---------- config / assets ----------
const BOARD_PATH = "../assets/game/table_board/";
const PIECES_PATH = "../assets/game/game_pieces/";
const CARDS_PATH = "../assets/game/game_cards/";
const BOARD_PNG = `${BOARD_PATH}chessboard.png`;
const OVERLAYS = {
    move: new Image(),
    capture: new Image(),
    fog: new Image()
};
OVERLAYS.move.src = `${BOARD_PATH}av_move.png`;
OVERLAYS.capture.src = `${BOARD_PATH}av_attk.png`;
OVERLAYS.fog.src = `${BOARD_PATH}fog_overlay.png`;

// Trigger re-render when overlays load
OVERLAYS.move.onload = () => {
    console.log('Move overlay loaded');
    render();
};
OVERLAYS.capture.onload = () => {
    console.log('Capture overlay loaded');
    render();
};
OVERLAYS.move.onerror = () => console.error('Failed to load move overlay:', OVERLAYS.move.src);
OVERLAYS.capture.onerror = () => console.error('Failed to load capture overlay:', OVERLAYS.capture.src);

const PIECE_SPRITE = (color, type) => `${PIECES_PATH}${color.toLowerCase()}_${type.toLowerCase()}_temp.png`;

// Card database - maps card IDs to full card data
// Card database - maps card IDs to full card data
const CARD_DATABASE = {
    // HIDDEN CARDS
    'mine': {
        id: 'mine',
        name: 'Mine',
        description: 'Places a hidden mine on a random empty square. Explodes when any piece steps on it, capturing all nearby pieces except kings. Dismantles after 4 turns if untouched.',
        image: 'mine.png'
    },
    'glue': {
        id: 'glue',
        name: 'Glue Trap',
        description: 'Place glue on a random tile. Any piece that lands on it becomes immobilized for 2 turns. Glue dries after 4 turns if unused.',
        image: 'glue.png'
    },
    'forbidden_lands': {
        id: 'forbidden_lands',
        name: 'Forbidden Lands',
        description: 'Creates a protective ring of tiles. Pieces inside cannot be captured; kings cannot enter; pieces leaving the zone cannot capture. Playing again while active summons a pawn in your back forbidden rank.',
        image: 'forbidden_lands.png'
    },
    'pawn_bomb': {
        id: 'pawn_bomb',
        name: 'Pawn Bomb',
        description: 'A random friendly pawn becomes a hidden bomb for up to 8 turns. If captured or its fuse runs out, it explodes in a 1-tile radius, capturing all nearby pieces. On its first move, the fuse shortens to 4 turns and it is revealed to you.',
        image: 'pawn_bomb.png'
    },
    'shroud': {
        id: 'shroud',
        name: 'Shroud',
        description: 'Swap two random friendly pieces\' position and appearance for 3 turns. If you have fewer than 2 pieces, summon a Peon safely first. Never swaps a king into check.',
        image: 'shroud.png'
    },
    'insurance': {
        id: 'insurance',
        name: 'Insurance',
        description: 'Select a piece to insure. When it is captured, summon glued Peons equal to half its value (rounded up). Peons cannot spawn in positions that would check the enemy king once unglued.',
        image: 'insurance.png'
    },
    
    // CURSE CARDS
    'eye_for_an_eye': {
        id: 'eye_for_an_eye',
        name: 'Eye for an Eye',
        description: 'Marks a friendly and opposing piece for 5 turns. Capturing a marked piece grants an extra turn immediately.',
        image: 'eye_for_an_eye.png'
    },
    'all_seeing': {
        id: 'all_seeing',
        name: 'All-Seeing',
        description: 'Summons an Effigy far from the enemy king. Every 3 turns it marks a random enemy piece for 1 turn.',
        image: 'all_seeing.png'
    },
    
    // TRANSFORM CARDS
    'pawn_scout': {
        id: 'pawn_scout',
        name: 'Pawn: Scout',
        description: 'Transform a pawn into a scout. Scouts move 5 squares in any direction and can mark enemy pieces. Capturing a marked piece grants an extra turn!',
        image: 'pawn_scout.png'
    },
    'knight_headhunter': {
        id: 'knight_headhunter',
        name: 'Knight: Headhunter',
        description: 'Transform a knight into a headhunter. Headhunters move like a king and project an attack 3 squares forward.',
        image: 'knight_headhunter.png'
    },
    'bishop_warlock': {
        id: 'bishop_warlock',
        name: 'Bishop: Warlock',
        description: 'Transform a bishop into a warlock. Warlocks blink to same-colored tiles (r=3), can step back 1, and gain Knight+Rook for 2 turns when an effigy dies.',
        image: 'bishop_warlock.png'
    },
    'queen_darklord': {
        id: 'queen_darklord',
        name: 'Queen: Dark Lord',
        description: 'Transform a Queen into a Dark Lord. The Dark Lord can enthrall nearby enemies (turning them into an ally) and suffers from daylight every 2 turns. Dies if enemy value ≤ 10.',
        image: 'queen_darklord.png'
    },
    'pawn_queen': {
        id: 'pawn_queen',
        name: 'Pawn: Queen',
        description: 'The pawn furthest from the enemy king transforms into a queen for 2 turns. After 2 turns, if on the last 3 ranks it becomes a peon; otherwise reverts to a pawn.',
        image: 'pawn_queen.png'
    },
    
    // SUMMON CARDS
    'summon_peon': {
        id: 'summon_peon',
        name: 'Summon Peon',
        description: 'Summons a friendly peon on a random square. Peons act like pawns but cannot promote.',
        image: 'summon_peon.png'
    },
    'summon_barricade': {
        id: 'summon_barricade',
        name: 'Summon Barricade',
        description: 'Place an uncapturable barricade on an empty square. Barricades block all movement and last for 5 turns.',
        image: 'summon_barricade.png'
    }

    //ADD ANY NEW CARDS WE IMPLEMENT HERE
};

// Helper to get full card data from ID
function getCardData(cardId) {
    return CARD_DATABASE[cardId] || {
        id: cardId,
        name: cardId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        description: 'Card description not available',
        image: 'card_back.png'
    };
}

// sounds
const clickOnAudio = document.getElementById('clickOn');
const clickOffAudio = document.getElementById('clickOff');
const menuMusic = document.getElementById('menuMusic');

function playClickOn() { try { clickOnAudio.currentTime = 0; clickOnAudio.volume = 0.7; clickOnAudio.play(); } catch(e){} }
function playClickOff(){ try { clickOffAudio.currentTime = 0; clickOffAudio.volume = 0.7; clickOffAudio.play(); } catch(e){} }

// start music on user interaction
document.addEventListener('click', () => { if (menuMusic.paused) { menuMusic.volume = 0.18; menuMusic.play().catch(()=>{}); } }, { once: true });

// ---------- canvas & rendering ----------
const canvas = document.getElementById('boardCanvas');
const ctx = canvas.getContext('2d', { alpha: true });

let dpr = Math.max(1, window.devicePixelRatio || 1);
let canvasPixelSize = 0;
let columns = 10;
let rows = 10;
let boardImg = new Image();
boardImg.src = BOARD_PNG;

// ---------- Piece sprite loading and caching ----------
const pieceImageCache = {}; // Cache loaded piece images

function loadPieceSprite(color, type) {
    // Create cache key
    const key = `${color}_${type}`;
    
    // Return cached image if it exists
    if (pieceImageCache[key]) {
        return pieceImageCache[key];
    }
    
    // Create new image using PIECE_SPRITE function
    const img = new Image();
    img.src = PIECE_SPRITE(color, type);
    
    // Cache it for future use
    pieceImageCache[key] = img;
    
    // When image loads, re-render to show it
    img.onload = () => {
        render();
    };
    
    img.onerror = () => {
        console.error(`Failed to load piece image: ${img.src}`);
        img.broken = true;
    };

    return img;
}

// Render board - wrapper around render() for clarity
function renderBoard() {
    render();
}

// compute sizes after CSS layout
function resizeCanvas(){
    const rect = canvas.getBoundingClientRect();
    canvasPixelSize = Math.min(rect.width, rect.height);
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;
    ctx.setTransform(dpr,0,0,dpr,0,0);
    render();
}

// Check if the board should be flipped (for black player's view)
function shouldFlipBoard() {
    return playerColor && playerColor.charAt(0).toUpperCase() === 'B';
}

window.addEventListener('resize', debounce(resizeCanvas, 80));
boardImg.onload = resizeCanvas;

// helpers: algebraic -> indices
function algebraicToIndex(pos){
    if(!pos) return null;
    const file = pos[0].toLowerCase();  // Changed toUpperCase() to toLowerCase()
    const rank = parseInt(pos.slice(1), 10);
    const col = file.charCodeAt(0) - 'a'.charCodeAt(0);  // Changed 'A' to 'a'
    const row = rows - rank;
    return { row, col };
}
function indexToAlgebraic(row, col){
    const file = String.fromCharCode('a'.charCodeAt(0) + col);
    const rank = (rows - row);
    return `${file}${rank}`;
}

// layout: inner board area with 1% border
function computeLayout(){
    const w = canvas.width / dpr;
    const h = canvas.height / dpr;
    
    const BOARD_IMAGE_SIZE = 1016;
    const BOARD_BORDER_PX = 8;
    
    const scale = Math.min(w, h) / BOARD_IMAGE_SIZE;
    
    // Scale the border proportionally
    const borderX = BOARD_BORDER_PX * scale;
    const borderY = BOARD_BORDER_PX * scale;
    
    const innerLeft = borderX;
    const innerTop = borderY;
    const innerW = w - borderX * 2;
    const innerH = h - borderY * 2;
    const cellSize = Math.min(innerW / columns, innerH / rows);
    const totalGridW = cellSize * columns;
    const totalGridH = cellSize * rows;
    
    // Center the grid
    const gridLeft = innerLeft + (innerW - totalGridW) / 2;
    const gridTop = innerTop + (innerH - totalGridH) / 2;
    
    return { w, h, borderX, borderY, innerLeft, innerTop, innerW, innerH, 
             cellSize, totalGridW, totalGridH, gridLeft, gridTop };
}

// convenience to get piece at grid
function getPieceAt(row, col){
    const pos = indexToAlgebraic(row, col);
    return gameState.board.find(p => p.position === pos && p.status === 'active' && p.type) || null;
}

function computeLegalMovesFor(piece){

    console.log('=== Computing legal moves for:', piece.id, piece);
    if (!piece.moves || piece.moves.length === 0) {
        return { moves: [], captures: [] };
    }

    console.log('  Piece has', piece.moves.length, 'moves from server');

    
    const moves = [];
    const captures = [];
    
    // Convert server move format to our row/col format
    for (const move of piece.moves) {
        const toSquare = move.to;
        // Convert {file: X, rank: Y} to algebraic
        const toAlgebraic = fileRankToAlgebraic(toSquare.file, toSquare.rank);
        const idx = algebraicToIndex(toAlgebraic);
        
        if (!idx) continue;
        
        // Check if destination has an enemy piece (capture) or is empty (move)
        const targetPiece = getPieceAt(idx.row, idx.col);
        if (targetPiece && targetPiece.color !== piece.color) {
            captures.push(idx);
        } else if (!targetPiece) {
            moves.push(idx);
        }
    }
    console.log('  Computed:', moves.length, 'moves,', captures.length, 'captures');
    console.log('  Move positions:', moves);
    console.log('  Capture positions:', captures);

    return { moves, captures };
}

// Helper function to convert file/rank to algebraic notation  
function fileRankToAlgebraic(file, rank) {
    // Server sends 0-indexed: file 0=A, 1=B, etc.
    // rank 0=1, 1=2, 2=3, etc.
    const fileChar = String.fromCharCode('A'.charCodeAt(0) + file);
    const rankNum = rank + 1;
    return `${fileChar.toLowerCase()}${rankNum}`;
}

// Helper to compare colors (handles "W"/"WHITE" and "B"/"BLACK")
function isSameColor(color1, color2) {
    const c1 = color1.charAt(0).toUpperCase();
    const c2 = color2.charAt(0).toUpperCase();
    return c1 === c2;
}

function reportMoveTiming() {
    if (!lastMoveSentAt) return;

    const afterUpdate = performance.now();

    // Wait until browser finishes PAINTING the updated board
    requestAnimationFrame(() => {
        const afterPaint = performance.now();
        const total = afterPaint - lastMoveSentAt;

        console.log(`[METRIC] Move round-trip + render = ${total.toFixed(2)} ms`);

        lastMoveSentAt = null; // reset
    });
}

let selectedPiece = null;
let legalMoves = [];
let legalCaptures = [];

// drawing
function render(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    const L = computeLayout();

    // Flip board 180° for black player
    if (shouldFlipBoard()) {
        ctx.save();
        ctx.translate(L.w / 2, L.h / 2);
        ctx.rotate(Math.PI);
        ctx.translate(-L.w / 2, -L.h / 2);
    }
  // draw board image stretched to canvas area but preserving the computed inner board area
    if(boardImg.complete){
    // fill entire canvas (fitted)
        ctx.drawImage(boardImg, 0, 0, L.w, L.h);
    } else {
        ctx.fillStyle = '#8a6b49';
        ctx.fillRect(0,0,L.w,L.h);
    }
    // Draw fog overlay on DMZ tiles (when DMZ is not active)
    if (!gameState.dmz && OVERLAYS.fog.complete) {
        ctx.save();
        
        // Top row (rank 10)
        for (let col = 0; col < columns; col++) {
            const x = L.gridLeft + col * L.cellSize;
            const y = L.gridTop;
            ctx.drawImage(OVERLAYS.fog, x, y, L.cellSize, L.cellSize);
        }
        
        // Bottom row (rank 1)
        for (let col = 0; col < columns; col++) {
            const x = L.gridLeft + col * L.cellSize;
            const y = L.gridTop + 9 * L.cellSize;
            ctx.drawImage(OVERLAYS.fog, x, y, L.cellSize, L.cellSize);
        }
        
        // Left column (file a) - skip corners already drawn
        for (let row = 1; row < 9; row++) {
            const x = L.gridLeft;
            const y = L.gridTop + row * L.cellSize;
            ctx.drawImage(OVERLAYS.fog, x, y, L.cellSize, L.cellSize);
        }
        
        // Right column (file j) - skip corners already drawn
        for (let row = 1; row < 9; row++) {
            const x = L.gridLeft + 9 * L.cellSize;
            const y = L.gridTop + row * L.cellSize;
            ctx.drawImage(OVERLAYS.fog, x, y, L.cellSize, L.cellSize);
        }
        
        ctx.restore();
    }

    // draw legal moves overlays
    console.log('Rendering overlays - legalMoves:', legalMoves.length, 'legalCaptures:', legalCaptures.length);
    ctx.save();
    ctx.globalCompositeOperation = 'source-over';
    for(const m of legalMoves){
        console.log('Drawing move indicator at row:', m.row, 'col:', m.col);
        const x = L.gridLeft + m.col*L.cellSize;
        const y = L.gridTop + m.row*L.cellSize;
        const img = OVERLAYS.move;
        console.log('Move image complete?', img.complete, 'src:', img.src);
        if (img.complete) {
            ctx.drawImage(img, x, y, L.cellSize, L.cellSize);
            console.log('Drew move overlay at', x, y);
        }
        else {
            console.log('Move overlay image not loaded yet');}
    }
    for(const m of legalCaptures){
        console.log('Drawing capture indicator at row:', m.row, 'col:', m.col);
        const x = L.gridLeft + m.col*L.cellSize;
        const y = L.gridTop + m.row*L.cellSize;
        const img = OVERLAYS.capture;
        console.log('Capture image complete?', img.complete, 'src:', img.src);
        if (img.complete) {
            ctx.drawImage(img, x, y, L.cellSize, L.cellSize);
            console.log('Drew capture overlay at', x, y);
        }
        else {
            console.log('Capture overlay image not loaded yet');}
    }
    ctx.restore();

    // draw pieces
    // draw pieces
for(const p of gameState.board){
    if(!p.position || p.status !== 'active') continue;
    const idx = algebraicToIndex(p.position);
    if(!idx) continue;
    const x = L.gridLeft + idx.col*L.cellSize;
    const y = L.gridTop + idx.row*L.cellSize;
    const pad = L.cellSize * 0.08;
    const img = loadPieceSprite(p.color, p.type);
    
    // If board is flipped, counter-rotate each piece to keep it upright
    if (shouldFlipBoard()) {
        ctx.save();
        const centerX = x + L.cellSize / 2;
        const centerY = y + L.cellSize / 2;
        ctx.translate(centerX, centerY);
        ctx.rotate(Math.PI); // Counter-rotate 180°
        ctx.translate(-centerX, -centerY);
    }
    
    // Only draw if image is complete and not broken
    if(img.complete && !img.broken){
        ctx.drawImage(img, x+pad, y+pad, L.cellSize - pad*2, L.cellSize - pad*2);
    } else if (!img.complete) {
        // Placeholder circle while loading
        ctx.fillStyle = p.color === 'WHITE' ? '#fff' : '#000';
        ctx.beginPath();
        ctx.arc(x + L.cellSize/2, y + L.cellSize/2, L.cellSize*0.36, 0, Math.PI*2);
        ctx.fill();
    }
    
    // if selected, add highlight
    if(selectedPiece && selectedPiece.id === p.id){
        ctx.strokeStyle = 'rgba(200,160,255,0.9)';
        ctx.lineWidth = Math.max(2, L.cellSize*0.04);
        ctx.strokeRect(x + L.cellSize*0.02, y + L.cellSize*0.02, L.cellSize*0.96, L.cellSize*0.96);
    }
    
    // Restore transformation if we counter-rotated
    if (shouldFlipBoard()) {
        ctx.restore();
    }
}
    // Restore transformation if board was flipped
    if (shouldFlipBoard()) {
        ctx.restore();
    }
}

// ---------- hit testing & input ----------
function pointerPosToCell(clientX, clientY){
    const rect = canvas.getBoundingClientRect();
    const L = computeLayout();
    let x = clientX - rect.left;
    let y = clientY - rect.top;
    
    // If board is flipped, we need to flip the mouse coordinates too
    if (shouldFlipBoard()) {
        x = L.w - x;
        y = L.h - y;
    }
    
    // check inner grid
    const gx = x - L.gridLeft;
    const gy = y - L.gridTop;
    if(gx < 0 || gy < 0) return null;
    const col = Math.floor(gx / L.cellSize);
    const row = Math.floor(gy / L.cellSize);
    if(col < 0 || col >= columns || row < 0 || row >= rows) return null;
    return { row, col };
}

canvas.addEventListener('mousedown', (ev) => {
    const cell = pointerPosToCell(ev.clientX, ev.clientY);
    playClickOn();
    if (!cell) return;
    
    // Handle tile targeting for cards
    if (waitingForTileTarget) {
        const { cardData, cardElement } = waitingForTileTarget;
        const targetSquare = indexToAlgebraic(cell.row, cell.col);
        
        const targetData = { target: targetSquare };  // Change 'square' to 'target'
        console.log('Playing card with tile target:', targetData);
        sendPlayCard(cardData.id, targetData);
        
        animateCardToDiscard(cardElement, cardData, () => {
            showCardOverlay(`Played: ${cardData.name} at ${targetSquare}`);
        });
        
        const me = gameState.players[0];
        me.hand = me.hand.filter(h => h !== cardData.id);
        renderHands();
        
        waitingForTileTarget = null;
        return;
    }
    
    if (!gameState.your_turn) {
        console.log("Not your turn!");
        return;
    }
    
    const clickedPiece = getPieceAt(cell.row, cell.col);
    const clickedAlgebraic = indexToAlgebraic(cell.row, cell.col);
    
    // Case 1: Clicked on one of our pieces - select it and show moves
    if (clickedPiece && isSameColor(clickedPiece.color, playerColor)) {
        selectedPiece = clickedPiece;
        const legal = computeLegalMovesFor(clickedPiece);
        legalMoves = legal.moves;
        legalCaptures = legal.captures;
        console.log('Selected piece:', selectedPiece.id, 'Legal moves:', legalMoves.length);
        render();
        return;
    }
    
    // Case 2: Have a piece selected - try to move it
    if (selectedPiece) {
        // Check if this is a legal move destination
        const isLegalMove = legalMoves.some(m => m.row === cell.row && m.col === cell.col);
        const isLegalCapture = legalCaptures.some(m => m.row === cell.row && m.col === cell.col);
        
        if (isLegalMove || isLegalCapture) {
            // This is a valid move - send it to server
            const fromAlgebraic = selectedPiece.position;
            const toAlgebraic = clickedAlgebraic;
            
            console.log('Attempting move:', fromAlgebraic, '→', toAlgebraic);
            sendMove(fromAlgebraic, toAlgebraic);
            
            // Clear selection (server will update game state)
            selectedPiece = null;
            legalMoves = [];
            legalCaptures = [];
            render();
        } else {
            // Not a legal move - deselect
            console.log('Not a legal move, deselecting');
            selectedPiece = null;
            legalMoves = [];
            legalCaptures = [];
            render();
        }
        return;
    }
    
    // Case 3: Clicked empty square with nothing selected - do nothing
    console.log('Clicked empty square');
});

canvas.addEventListener('mouseup', (ev) => {
            playClickOff();
});

function tryMoveTo(row,col){
  // check if destination is legal
  if(legalMoves.some(m => m.row===row && m.col===col) || legalCaptures.some(m => m.row===row && m.col===col)){
    // perform move
    const from = algebraicToIndex(selectedPiece.position);
    const toAlgebraic = indexToAlgebraic(row,col);
    // capture?
    const occupant = getPieceAt(row,col);
    if(occupant){
      // set occupant status to captured and add to capturing player's captured_pieces
      occupant.status = "captured";
      // this assumes player is player 1
      const player = gameState.players.find(pl => pl.player_id === 'p1');
      if(player) player.captured_pieces.push({ type: occupant.type, color: occupant.color, position: null, status: 'captured' });
    }
    // update piece position
    selectedPiece.position = toAlgebraic;
    // update logs
    gameState.logs.push({ turn: gameState.logs.length+1, player_id: 'p1', action: 'move_piece', details: `${selectedPiece.id}:${selectedPiece.position}` });
    // clear selection
            selectedPiece = null;
            legalMoves = [];
            legalCaptures = [];
    // end turn after movement or card
    endTurn();
                render();
            } else {
    // not legal: cancel
                selectedPiece = null;
                legalMoves = [];
                legalCaptures = [];
                render();
            }
        }

// ---------- card DOM handling ----------
const playerHandEl = document.getElementById('playerHand');
const opponentHandEl = document.getElementById('opponentHand');
const cardOverlay = document.getElementById('cardPlayOverlay');
const drawBtn = document.getElementById('drawCardBtn');

// rendering hands
function renderHands(){
    const me = gameState.players[0];
    const opp = gameState.players[1];

    // Clear existing cards
    playerHandEl.innerHTML = '';
    opponentHandEl.innerHTML = '';
    
    // Render opponent's hand (card backs) - HORIZONTAL layout
    const oppHandSize = opp.hand_size || opp.hand.length;
    opponentHandEl.innerHTML = '';
    opponentHandEl.style.display = 'flex';
    opponentHandEl.style.flexDirection = 'row';
    opponentHandEl.style.gap = '8px';
    opponentHandEl.style.justifyContent = 'center';

    for (let i = 0; i < oppHandSize; i++) {
        const cardEl = document.createElement('div');
        cardEl.className = 'card';
        cardEl.style.width = '72px';
        cardEl.style.height = '96px';
        cardEl.style.backgroundImage = `url('${CARDS_PATH}card-back.png')`;
        cardEl.style.backgroundSize = 'cover';
        opponentHandEl.appendChild(cardEl);
    }

    // Render player's hand (full cards with details)
    me.hand.forEach((cardId, idx) => {
        const cardData = getCardData(cardId);
        const el = document.createElement('div');
        el.className = 'card';
        el.dataset.id = cardData.id;
        
        // Build card with existing CSS classes
        el.innerHTML = `
            <div class="card-inner">
                <div class="front">
                    <div class="title">${cardData.name}</div>
                    <div class="desc">${cardData.description}</div>
                </div>
            </div>`;
        
        // Hover enlarge
        el.addEventListener('mouseenter', () => {
            document.querySelectorAll('.card.hovered').forEach(c=>c.classList.remove('hovered'));
            el.classList.add('hovered');
        });
        el.addEventListener('mouseleave', () => {
            el.classList.remove('hovered');
        });
        
        // Click = play card
        el.addEventListener('mousedown', (ev) => { playClickOn(); });
        el.addEventListener('mouseup', (ev) => { playClickOff(); });
        el.addEventListener('click', (ev) => {
            playCard(cardData, el);
        });
        
        playerHandEl.appendChild(el);
    });
}

// Show card in discard pile
function showCardInDiscard(cardData) {
    const discardSlot = document.getElementById('discardCard');
    if (!discardSlot) return;
    
    // Create card with same structure as hand cards
    discardSlot.innerHTML = `
        <div class="card">
            <div class="card-inner" style="background-image: url('assets/game/cards/card-front-default.png'); background-size: cover;">
                <div class="title">${cardData.name}</div>
                <div class="desc">${cardData.description}</div>
            </div>
        </div>
    `;
    
    console.log('Discard pile updated with:', cardData.name);
}

// Animate card flying to discard pile
function animateCardToDiscard(sourceElement, cardData, onComplete) {
    // Get positions
    const sourceRect = sourceElement.getBoundingClientRect();
    const discardSlot = document.getElementById('discardCard');
    if (!discardSlot) {
        if (onComplete) onComplete();
        return;
    }
    
    const targetRect = discardSlot.getBoundingClientRect();
    
    // Create flying card clone
    const flyingCard = sourceElement.cloneNode(true);
    flyingCard.classList.add('flying');
    flyingCard.style.left = `${sourceRect.left}px`;
    flyingCard.style.top = `${sourceRect.top}px`;
    flyingCard.style.width = `${sourceRect.width}px`;
    flyingCard.style.height = `${sourceRect.height}px`;
    
    // Calculate translation
    const tx = targetRect.left - sourceRect.left + (targetRect.width - sourceRect.width) / 2;
    const ty = targetRect.top - sourceRect.top + (targetRect.height - sourceRect.height) / 2;
    
    flyingCard.style.setProperty('--tx', `${tx}px`);
    flyingCard.style.setProperty('--ty', `${ty}px`);
    
    document.body.appendChild(flyingCard);
    
    // Remove flying card and show in discard after animation
    setTimeout(() => {
        document.body.removeChild(flyingCard);
        showCardInDiscard(cardData);
        if (onComplete) onComplete();
    }, 600);
}

// Handle opponent playing a card
function handleOpponentCardPlay(cardId) {
    const cardData = getCardData(cardId);
    const opponentHandEl = document.getElementById('opponentHand');
    
    if (!opponentHandEl || opponentHandEl.children.length === 0) {
        // No cards to animate from, just show in discard
        showCardInDiscard(cardData);
        return;
    }
    
    // Animate the first card from opponent's hand
    const firstCard = opponentHandEl.children[0];
    animateCardToDiscard(firstCard, cardData);
    
    // Show overlay
    const cardOverlay = document.getElementById('cardPlayOverlay');
    cardOverlay.textContent = `Opponent played: ${cardData.name}`;
    cardOverlay.style.opacity = '1';
    cardOverlay.setAttribute('aria-hidden','false');
    setTimeout(()=>{ 
        cardOverlay.style.opacity = '0'; 
        cardOverlay.setAttribute('aria-hidden','true'); 
    }, 1200);
}

function playCard(cardData, cardElement){
    if (!gameState.your_turn) {
        console.log('Not your turn!');
        return;
    }
    
    const needsTarget = cardNeedsTarget(cardData.id);
    
    if (needsTarget === 'piece') {
        if (!selectedPiece) {
            alert(`Please select a ${cardData.name === 'Pawn Scout' ? 'pawn' : 'piece'} first!`);
            return;
        }
        
        // Validate piece type if needed
        if (cardData.id === 'pawn_scout' && selectedPiece.type !== 'PAWN') {
            alert('This card can only be used on pawns!');
            return;
        }
        
        // Build target data based on card type
        const targetData = buildTargetData(cardData.id, selectedPiece);
        
        console.log('Playing card with target:', targetData);
        
        // ONLY send to server - don't update UI yet
        sendPlayCard(cardData.id, targetData, cardElement, cardData);
        
        // Clear selection
        selectedPiece = null;
        legalMoves = [];
        legalCaptures = [];
        render();
        
    } else if (needsTarget === 'tile') {
        // Card needs a tile click (like placing a mine)
        alert(`Click on a tile to place ${cardData.name}`);
        // Set a flag to wait for tile click
        waitingForTileTarget = { cardData, cardElement };
        return;
        
    } else {
        // No target needed - just send to server
        console.log('Playing card with no target');
        sendPlayCard(cardData.id, {}, cardElement, cardData);
    }

    //wait for server confirmation to update hand
}

// Helper to build the right target format for each card
function buildTargetData(cardId, selectedPiece) {
    // Most transformation and piece-targeting cards use "target"
    const targetCards = [
        'pawn_scout',
        'knight_headhunter',
        'bishop_warlock', 
        'queen_darklord',
        'transmute',
        'insurance',
        'exhaustion'
    ];
    
    if (targetCards.includes(cardId)) {
        return { target: selectedPiece.position };
    }
    
    // Special case for of_flesh_and_blood
    if (cardId === 'of_flesh_and_blood') {
        return { piece_id: selectedPiece.id };
    }
    
    // Default format
    return { target: selectedPiece.position };
}

// Helper to determine if card needs targeting
// Helper to determine if card needs targeting
function cardNeedsTarget(cardId) {
    // Cards that target a single piece
    const pieceCards = [
        'pawn_scout',
        'knight_headhunter',
        'bishop_warlock',
        'queen_darklord',
        'transmute',
        'of_flesh_and_blood',
        'insurance',
        'exhaustion'
    ];
    
    // Cards that target an empty square/tile
    const tileCards = [
        'summon_barricade'
    ];
    
    // Cards with special/complex targeting (need custom UI)
    const specialCards = [
        'eye_for_an_eye',  // Needs 2 pieces (friendly + enemy)
        'eye_of_ruin'       // Needs hand interaction
    ];
    
    if (pieceCards.includes(cardId)) return 'piece';
    if (tileCards.includes(cardId)) return 'tile';
    if (specialCards.includes(cardId)) return 'special';  // Handle these separately
    
    // Cards with no targeting needed:
    // mine, forced_move, forbidden_lands, summon_peon, shroud, all_seeing,
    // pawn_queen, pawn_bomb, glue
    return 'none';
}

// Helper for card overlay
function showCardOverlay(text) {
    const cardOverlay = document.getElementById('cardPlayOverlay');
    cardOverlay.textContent = text;
    cardOverlay.style.opacity = '1';
    cardOverlay.setAttribute('aria-hidden','false');
    setTimeout(()=>{ 
        cardOverlay.style.opacity = '0'; 
        cardOverlay.setAttribute('aria-hidden','true'); 
    }, 1200);
}

// Add this at the top with other globals
let waitingForTileTarget = null;

// ---------- turn / sync ----------
// TODO: add this
function endTurn(){
  // gameState.players.forEach(p => p.clock_active = !p.clock_active);
  console.log('Turn ended. State:', gameState);
  // place to call backend sync API:
  // fetch('/api/game/update', {method:'POST', body: JSON.stringify(gameState)});
    }

// ---------- UI initialization ----------


function initUI(){
  document.getElementById('playerName').textContent = gameState.players[0].name;
  document.getElementById('opponentName').textContent = gameState.players[1].name;
  renderHands();
}

// Complete UI refresh based on current gameState
function updateFullUI() {
    console.log('=== updateFullUI called ===');
    console.log('Current gameState:', JSON.stringify(gameState, null, 2));
    
    // Safety check - make sure we have player data
    if (!gameState.players || gameState.players.length < 2) {
        console.error('Cannot update UI: player data not ready');
        console.log('gameState.players:', gameState.players);
        return;
    }
    
    console.log('Updating UI with valid game state');

    // 1. Update player information displays
    updatePlayerInfo();
    
    // 2. Render the chess board with all pieces
    renderBoard();
    
    // 3. Render player hands
    renderHands();
    
    // 4. Update turn indicator
    updateTurnIndicator();
    
    // 5. Update timers if you have them
    if (gameState.white_time !== undefined && gameState.black_time !== undefined) {
        syncTimer(gameState.white_time, gameState.black_time);
        if (!timerInterval) {
            startTimer();
        }
    }
}



// Update player names and deck information
function updatePlayerInfo() {
    // Player (you)
    document.getElementById('playerName').textContent = gameState.players[0].name;
    const playerDeckCount = document.getElementById('playerDeckCount');
    if (playerDeckCount) {
        playerDeckCount.textContent = `Deck: ${gameState.players[0].deck_size}`;
    }
    
    // Opponent
    document.getElementById('opponentName').textContent = gameState.players[1].name;
    const opponentDeckCount = document.getElementById('opponentDeckCount');
    if (opponentDeckCount) {
        opponentDeckCount.textContent = `Deck: ${gameState.players[1].deck_size}`;
    }
}

// Update turn indicator to show whose turn it is
function updateTurnIndicator() {
    const turnIndicator = document.getElementById('turnIndicator');
    if (!turnIndicator) return;
    
    if (gameState.your_turn) {
        turnIndicator.textContent = 'Your Turn';
        turnIndicator.classList.add('your-turn');
        turnIndicator.classList.remove('opponent-turn');
    } else {
        turnIndicator.textContent = "Opponent's Turn";
        turnIndicator.classList.add('opponent-turn');
        turnIndicator.classList.remove('your-turn');
    }
}

// Update timer displays
function updateTimers() {
    const topTimer = document.getElementById('timerTop');
    const bottomTimer = document.getElementById('playerTimer');
    
    if (!topTimer || !bottomTimer) return;
    if (gameState.white_time === undefined || gameState.black_time === undefined) return;
    
    // If you're white, your timer is at bottom, opponent (black) at top
    // If you're black, your timer is at bottom, opponent (white) at top
    if (playerColor && playerColor.charAt(0).toUpperCase() === 'W') {
        // You are white
        bottomTimer.textContent = formatTime(Math.ceil(gameState.white_time));
        topTimer.textContent = formatTime(Math.ceil(gameState.black_time));
    } else if (playerColor && playerColor.charAt(0).toUpperCase() === 'B') {
        // You are black
        bottomTimer.textContent = formatTime(Math.ceil(gameState.black_time));
        topTimer.textContent = formatTime(Math.ceil(gameState.white_time));
    }
}

// Helper to format seconds into MM:SS or HH:MM:SS
function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Start the game timer
function startTimer() {
    // Clear any existing timer
    if (timerInterval) {
        clearInterval(timerInterval);
    }
    
    lastTimerUpdate = Date.now();
    
    // Update timer every 100ms for smooth countdown
    timerInterval = setInterval(() => {
        const now = Date.now();
        const deltaSeconds = (now - lastTimerUpdate) / 1000;
        lastTimerUpdate = now;
        
        // Decrement the time for whichever player's turn it is
        if (gameState.current_turn === 'W') {
            gameState.white_time = Math.max(0, gameState.white_time - deltaSeconds);
        } else {
            gameState.black_time = Math.max(0, gameState.black_time - deltaSeconds);
        }
        
        // Update display
        updateTimers();
        
        // Check for time out
        if (gameState.white_time <= 0 || gameState.black_time <= 0) {
            clearInterval(timerInterval);
            console.log('Time ran out!');
        }
    }, 100);
    
    console.log('✓ Timer started');
}

// Stop the timer
function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
        console.log('Timer stopped');
    }
}

// Sync timer with server time
function syncTimer(serverWhiteTime, serverBlackTime) {
    gameState.white_time = serverWhiteTime;
    gameState.black_time = serverBlackTime;
    lastTimerUpdate = Date.now();
    updateTimers();
    console.log('Timer synced:', { white: serverWhiteTime, black: serverBlackTime });
}

// ---------- utility: debounce ----------
function debounce(fn, t=100){
    let id;
    return (...a) => { clearTimeout(id); id = setTimeout(()=>fn(...a), t); };
}

// initial sizing & render
window.addEventListener('load', () => {
    dpr = Math.max(1, window.devicePixelRatio || 1);
    // columns and rows are always 10 for the board
    resizeCanvas();
});

console.log('=== Game.js loaded ===');

// Initialize the game when page loads
window.addEventListener('DOMContentLoaded', () => {
    console.log('=== DOM loaded, initializing game ===');
    
    // Parse URL parameters
    const paramsValid = parseURLParams();
    if (!paramsValid) {
        console.error('Failed to parse URL parameters');
        return;
    }
    
    console.log('URL parameters parsed:', { gameId, playerId });
    
    // Connect to game server via WebSocket
    console.log('Attempting to connect to game server...');
    connectToGame();
});

// Clean up timer when page unloads
window.addEventListener('beforeunload', () => {
    stopTimer();
});