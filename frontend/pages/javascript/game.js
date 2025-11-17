
// gamestate json
const gameState = {
  // pull gamestate from json
};

// ---------- config / assets ----------
const BOARD_PATH = "../assets/game/table_board/";
const PIECES_PATH = "../assets/game/game_pieces/";
const CARDS_PATH = "../assets/game/game_cards/";
const BOARD_PNG = `${BOARD_PATH}chessboard.png`;
const OVERLAYS = {
  move: new Image(),
  capture: new Image()
};
OVERLAYS.move.src = `${BOARD_PATH}av_move.png`;
OVERLAYS.capture.src = `${BOARD_PATH}av_attk.png`;

const PIECE_SPRITE = (color, type) => `${PIECES_PATH}${color.toLowerCase()}_${type.toLowerCase()}_temp.png`;

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
let columns = gameState.dmz ? 9 : 8;
let rows = columns;
let boardImg = new Image();
boardImg.src = BOARD_PNG;

// TODO: add rendering for pieces

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
window.addEventListener('resize', debounce(resizeCanvas, 80));
boardImg.onload = resizeCanvas;

// helpers: algebraic -> indices
function algebraicToIndex(pos){
  if(!pos) return null;
  const file = pos[0].toUpperCase();
  const rank = parseInt(pos.slice(1), 10);
  // determine mapping: files A.. based on columns (A..I)
  const col = file.charCodeAt(0) - 'A'.charCodeAt(0);
  // algebraic rank 1 = bottom row. canvas row 0 = top, so row = rows - rank
  const row = rows - rank;
  return { row, col };
}
function indexToAlgebraic(row, col){
  const file = String.fromCharCode('A'.charCodeAt(0) + col);
  const rank = (rows - row);
  return `${file}${rank}`;
}

// layout: inner board area with 1% border
function computeLayout(){
  const w = canvas.width / dpr;
  const h = canvas.height / dpr;
  // board must fill canvas; but we maintain 1% border inside
  const borderX = w * 0.01;
  const borderY = h * 0.01;
  const innerLeft = borderX;
  const innerTop = borderY;
  const innerW = w - borderX*2;
  const innerH = h - borderY*2;
  const cellSize = Math.min(innerW / columns, innerH / rows);
  const totalGridW = cellSize * columns;
  const totalGridH = cellSize * rows;
  // center the grid inside inner area
  const gridLeft = innerLeft + (innerW - totalGridW)/2;
  const gridTop = innerTop + (innerH - totalGridH)/2;
  return { w,h, borderX, borderY, innerLeft, innerTop, innerW, innerH, cellSize, totalGridW, totalGridH, gridLeft, gridTop };
}

// convenience to get piece at grid
function getPieceAt(row, col){
  const pos = indexToAlgebraic(row, col);
  return gameState.board.find(p => p.position === pos && p.status === 'active' && p.type) || null;
}

// TODO: pull logic from json and get legal moves for each piece
function computeLegalMovesFor(piece){
  const start = algebraicToIndex(piece.position);
  if(!start) return { moves: [], captures: [] };
    let dirs = [];
    if(piece.type == 'wl'){
      // TODO: add logic
    }
    const moves = [];
    const captures = [];
  for(const [dr,dc] of dirs){
    const r = start.row + dr;
    const c = start.col + dc;
    if(r < 0 || r >= rows || c < 0 || c >= columns) continue;
    const occupant = getPieceAt(r,c);
    if(!occupant) moves.push({row:r,col:c});
    else if(occupant.color !== piece.color) captures.push({row:r,col:c});
  }
  return { moves, captures };
}

let selectedPiece = null;
let legalMoves = [];
let legalCaptures = [];

// drawing
function render(){
  ctx.clearRect(0,0,canvas.width,canvas.height);
  const L = computeLayout();

  // draw board image stretched to canvas area but preserving the computed inner board area
  if(boardImg.complete){
    // fill entire canvas (fitted)
    ctx.drawImage(boardImg, 0, 0, L.w, L.h);
  } else {
    ctx.fillStyle = '#8a6b49';
    ctx.fillRect(0,0,L.w,L.h);
  }

  // draw DMZ outer ring if dmz true
  if(gameState.dmz){
  }

  // draw legal moves overlays
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  for(const m of legalMoves){
    const x = L.gridLeft + m.col*L.cellSize;
    const y = L.gridTop + m.row*L.cellSize;
    const img = OVERLAYS.move;
    ctx.drawImage(img, x, y, L.cellSize, L.cellSize);
  }
  for(const m of legalCaptures){
    const x = L.gridLeft + m.col*L.cellSize;
    const y = L.gridTop + m.row*L.cellSize;
    const img = OVERLAYS.capture;
    ctx.drawImage(img, x, y, L.cellSize, L.cellSize);
  }
  ctx.restore();

  // draw pieces
  for(const p of gameState.board){
    if(!p.position || p.status !== 'active') continue;
    const idx = algebraicToIndex(p.position);
    if(!idx) continue;
    const x = L.gridLeft + idx.col*L.cellSize;
    const y = L.gridTop + idx.row*L.cellSize;
    const pad = L.cellSize * 0.08;
    const img = loadPieceSprite(p.color, p.type);
    if(img.complete){
      // draw centered with padding
      ctx.drawImage(img, x+pad, y+pad, L.cellSize - pad*2, L.cellSize - pad*2);
    } else {
      // placeholder circle
      ctx.fillStyle = p.color === 'w' ? '#fff' : '#000';
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
  }
}

// ---------- hit testing & input ----------
function pointerPosToCell(clientX, clientY){
  const rect = canvas.getBoundingClientRect();
  const L = computeLayout();
  const x = clientX - rect.left;
  const y = clientY - rect.top;
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
  if(!cell) return;
  const piece = getPieceAt(cell.row, cell.col);
  if(piece && piece.color === 'w'){ // replace with player color
    selectedPiece = piece;
    const legal = computeLegalMovesFor(piece);
    legalMoves = legal.moves;
    legalCaptures = legal.captures;
    render();
  } else {
    // clicked on empty or enemy - if selected, maybe move
    if(selectedPiece){
      tryMoveTo(cell.row, cell.col);
    }
  }
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

  playerHandEl.innerHTML = '';
  opp.hand.forEach(c => {
    // TODO: replace with back of card png
    const cardEl = document.createElement('div');
    cardEl.className = 'card';
    cardEl.style.width = '72px'; cardEl.style.height='96px';
    cardEl.innerHTML = `<div class="card-inner"><div class="front"></div><div class="back"></div></div>`;
    opponentHandEl.appendChild(cardEl);
  });

  me.hand.forEach((card, idx) => {
    const el = document.createElement('div');
    el.className = 'card';
    el.dataset.id = card.id;
    el.innerHTML = `
      <div class="card-inner">
        <div class="front">
          <div class="title">${card.name}</div>
        </div>
        <div class="back">
          <div class="title">${card.name}</div>
          <div class="desc">${card.description}</div>
        </div>
      </div>`;
    // hover enlarge
    el.addEventListener('mouseenter', () => {
      document.querySelectorAll('.card.hovered').forEach(c=>c.classList.remove('hovered'));
      el.classList.add('hovered');
    });
    el.addEventListener('mouseleave', () => {
      el.classList.remove('hovered');
    });
    // click = play card
    el.addEventListener('mousedown', (ev) => { playClickOn(); });
    el.addEventListener('mouseup', (ev) => { playClickOff(); });
    el.addEventListener('click', (ev) => {
      playCard(card, el);
    });
    playerHandEl.appendChild(el);
  });
}

function playCard(card, el){
  // show overlay with card name
  cardOverlay.textContent = `Played: ${card.name}`;
  cardOverlay.style.opacity = '1';
  cardOverlay.setAttribute('aria-hidden','false');
  setTimeout(()=>{ cardOverlay.style.opacity = '0'; cardOverlay.setAttribute('aria-hidden','true'); }, 1200);

  // need to add method to play cards to affect gamestate
  if(card.name.toLowerCase().includes('dmz')){
    gameState.dmz = true;
    columns = gameState.dmz ? 9 : 8;
    rows = columns;
  }

  // remove card from hand and add to discard
  const me = gameState.players[0];
  me.hand = me.hand.filter(h => h.id !== card.id);
  me.discard_pile_top = card;
  gameState.logs.push({ turn: gameState.logs.length+1, player_id: me.player_id, action: 'play_card', details: `Played ${card.name}` });

  renderHands();
  render();
  endTurn();
}

// draw card animation
drawBtn.addEventListener('click', () => {
  const me = gameState.players[0];
  // create method to pull random card from deck here
  const newCard = { id: 'c'+(Date.now()%10000), name: 'Card_Name', description: 'Placeholder_Card_Description', type:'Action', target:'board' };
  // animate from deckPreview to hand
  const deckPreview = document.getElementById('deckPreview');
  const rect = deckPreview.getBoundingClientRect();
  const temp = document.createElement('div');
  temp.className = 'card';
  temp.style.position = 'fixed';
  temp.style.left = `${rect.left + rect.width/2 - 60}px`;
  temp.style.top = `${rect.top + rect.height/2 - 80}px`;
  temp.style.transform = 'translateZ(0)';
  temp.innerHTML = `<div class="card-inner"><div class="front"><div class="title">${newCard.name}</div></div><div class="back"></div></div>`;
  document.body.appendChild(temp);

  // compute target spot (end of player hand)
  const handRect = playerHandEl.getBoundingClientRect();
  const targetX = handRect.left + (handRect.width/2);
  const targetY = handRect.top + (handRect.height/2);

  // animate with simple JS
  // TODO: replace with actual animation
  temp.animate([
    { transform: `translate(0px,0px) scale(1)` },
    { transform: `translate(${targetX - rect.left}px, ${targetY - rect.top}px) scale(0.9)` }
  ], { duration: 550, easing: 'cubic-bezier(.2,.9,.2,1)' });

  setTimeout(()=> {
    document.body.removeChild(temp);
    me.hand.push(newCard);
    renderHands();
  }, 600);
});

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

// ---------- utility: debounce ----------
function debounce(fn, t=100){
  let id;
  return (...a) => { clearTimeout(id); id = setTimeout(()=>fn(...a), t); };
}

// initial sizing & render
window.addEventListener('load', () => {
  dpr = Math.max(1, window.devicePixelRatio || 1);
  columns = gameState.dmz ? 9 : 8;
  rows = columns;
  initUI();
  resizeCanvas();
});
