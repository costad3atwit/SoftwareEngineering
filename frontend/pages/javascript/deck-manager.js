// ============================================================================
// DECK MANAGER - Shared utilities for deck selection and storage
// ============================================================================


/**
 * Deck configuration
 */
const DECK_SIZE = 16;
const MAX_COPIES_PER_CARD = 3;
const DECK_STORAGE_KEY = 'arcane_chess_player_deck';

/**
 * Default deck used when no custom deck is saved
 */
const DEFAULT_DECK = [
    "forbidden_lands", "eye_for_an_eye", "summon_peon", "pawn_scout",
    "knight_headhunter", "bishop_warlock",
    "mine", "eye_for_an_eye", "summon_peon", "pawn_scout",
    "knight_headhunter", "bishop_warlock",
    "forbidden_lands", "eye_for_an_eye", "summon_peon", "pawn_scout"
];

/**
 * All available cards for deck building
 * Format: { id, name, category, description }
 */
const AVAILABLE_CARDS = {
    // HIDDEN CARDS
    'mine': { name: 'Mine', category: 'HIDDEN' },
    'glue': { name: 'Glue Trap', category: 'HIDDEN' },
    'forbidden_lands': { name: 'Forbidden Lands', category: 'HIDDEN' },
    'pawn_bomb': { name: 'Pawn Bomb', category: 'HIDDEN' },
    'shroud': { name: 'Shroud', category: 'HIDDEN' },
    'insurance': { name: 'Insurance', category: 'HIDDEN' },
    
    // CURSE CARDS
    'eye_for_an_eye': { name: 'Eye for an Eye', category: 'CURSE' },
    'all_seeing': { name: 'All-Seeing', category: 'CURSE' },
    'exhaustion': { name: 'Exhaustion', category: 'CURSE' },
    
    // TRANSFORM CARDS
    'pawn_scout': { name: 'Pawn: Scout', category: 'TRANSFORM' },
    'knight_headhunter': { name: 'Knight: Headhunter', category: 'TRANSFORM' },
    'bishop_warlock': { name: 'Bishop: Warlock', category: 'TRANSFORM' },
    'queen_darklord': { name: 'Queen: Dark Lord', category: 'TRANSFORM' },
    'pawn_queen': { name: 'Pawn: Queen', category: 'TRANSFORM' },
    'transmute': { name: 'Transmute', category: 'TRANSFORM' },
    'rook_cleric': { name: 'Rook: Cleric', category: 'TRANSFORM' }, 
    'bishop_witch': { name: 'Bishop: Witch', category: 'TRANSFORM' }, 
    
    // SUMMON CARDS
    'summon_peon': { name: 'Summon Peon', category: 'SUMMON' },
    'summon_barricade': { name: 'Summon Barricade', category: 'SUMMON' },
    
    // FORCED CARDS
    'forced_move': { name: 'Forced Move', category: 'FORCED' },
    'eye_of_ruin': { name: 'Eye of Ruin', category: 'FORCED' },

    // UNSTABLE CARDS
    'of_flesh_and_blood': { name: 'Of Flesh and Blood', category: 'UNSTABLE' }
};

/**
 * Get the storage key for the current player's deck
 * @param {string} playerId - The player's ID
 * @returns {string} Storage key
 */
function getDeckStorageKey(playerId) {
    if (!playerId) {
        console.warn('No player ID provided, using default key');
        return DECK_STORAGE_KEY; // Fallback to default
    }
    return `${DECK_STORAGE_KEY}_${playerId}`;
}

function loadDeck(playerId) {
    const storageKey = getDeckStorageKey(playerId);

    try {
        const stored = localStorage.getItem(storageKey);
        if (stored) {
            const deck = JSON.parse(stored);
            const validation = validateDeck(deck);
            // Validate deck
            if (validation.valid) {
                console.log(`✓ Loaded custom deck for ${playerId}:`, deck);
                return deck;
            } else {
                console.warn('Stored deck invalid:', validation.error);
            }
        }
    } catch (error) {
        console.error('Error loading deck from storage:', error);
    }
    
    // Return default deck if no valid deck stored
    console.log(`Using default deck for ${playerId}`);
    console.warn("Invalid deck found → resetting to default deck.");
    saveDeck(DEFAULT_DECK, playerId);  // ← Add playerId here
    return [...DEFAULT_DECK];
}

/**
 * Save the player's deck to localStorage
 * @param {Array<string>} deck - Array of exactly 16 card IDs
 * @param {string} playerId - The player's ID
 * @returns {boolean} Success status
 */
function saveDeck(deck, playerId) {
    const { valid, error } = validateDeck(deck);
    if (!valid) {
        console.error('Cannot save deck:', error);
        return false;
    }
    
    const storageKey = getDeckStorageKey(playerId);
    
    try {
        localStorage.setItem(storageKey, JSON.stringify(deck));
        console.log(`Deck saved for ${playerId}:`, deck);
        return true;
    } catch (error) {
        console.error('Error saving deck to storage:', error);
        return false;
    }
}

/**
 * Get the currently active deck (loads from storage)
 * This is the function that should be called when queueing/challenging
 * @returns {Array<string>} Array of 16 card IDs
 */
function getDeck(playerId) {
    return loadDeck(playerId);
}

/**
 * Reset deck to default
 * @param {string} playerId - The player's ID
 * @returns {boolean} Success status
 */
function resetDeck(playerId) {
    return saveDeck(DEFAULT_DECK, playerId);
}

/**
 * Check if a deck is currently saved (not using default)
 * @param {string} playerId - The player's ID
 * @returns {boolean} True if custom deck is saved
 */
function hasCustomDeck(playerId) {
    try {
        const storageKey = getDeckStorageKey(playerId);
        const stored = localStorage.getItem(storageKey);
        return stored !== null;
    } catch (error) {
        return false;
    }
}

/**
 * Get card information by ID
 * @param {string} cardId - The card ID
 * @returns {Object|null} Card info or null if not found
 */
function getCardInfo(cardId) {
    if (cardId in AVAILABLE_CARDS) {
        return {
            id: cardId,
            ...AVAILABLE_CARDS[cardId]
        };
    }
    return null;
}

/**
 * Get all available cards (for deck builder UI)
 * @returns {Array<Object>} Array of card objects with id, name, category
 */
function getAllCards() {
    return Object.keys(AVAILABLE_CARDS).map(id => ({
        id: id,
        ...AVAILABLE_CARDS[id]
    }));
}

/**
 * Validate a deck
 * @param {Array<string>} deck - Deck to validate
 * @returns {Object} { valid: boolean, error: string|null }
 */
function validateDeck(deck) {
    if (!Array.isArray(deck)) {
        return { valid: false, error: 'Deck must be an array' };
    }
    
    if (deck.length !== DECK_SIZE) {
        return { 
            valid: false, 
            error: `Deck must contain exactly ${DECK_SIZE} cards (got ${deck.length})` 
        };
    }
    
    const invalidCards = deck.filter(cardId => !(cardId in AVAILABLE_CARDS));
    if (invalidCards.length > 0) {
        return { 
            valid: false, 
            error: `Invalid card IDs: ${invalidCards.join(', ')}` 
        };
    }

    // Enforce max copies per card
    const counts = {};
    for (const cardId of deck) {
        counts[cardId] = (counts[cardId] || 0) + 1;
    }

    const overLimit = Object.entries(counts)
        .filter(([_, count]) => count > MAX_COPIES_PER_CARD);

    if (overLimit.length > 0) {
        const details = overLimit
            .map(([id, count]) => `${id} (${count} copies)`)
            .join(', ');
        return {
            valid: false,
            error: `Too many copies of one or more cards (max ${MAX_COPIES_PER_CARD} each): ${details}`
        };
    }
    
    return { valid: true, error: null };
}

// Log that deck manager is loaded
console.log('  Deck Manager loaded');
// console.log(`  Current deck: ${hasCustomDeck() ? 'Custom' : 'Default'}`);
console.log(`  Deck size: ${DECK_SIZE}, max copies per card: ${MAX_COPIES_PER_CARD}`);