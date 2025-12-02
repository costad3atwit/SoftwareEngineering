// ============================================================================
// DECK MANAGER - Shared utilities for deck selection and storage
// ============================================================================

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
    
    // UNSTABLE CARDS
    'of_flesh_and_blood': { name: 'Of Flesh and Blood', category: 'UNSTABLE' }
};

/**
 * LocalStorage key for storing the player's deck
 */
const DECK_STORAGE_KEY = 'arcane_chess_player_deck';

/**
 * Load the player's deck from localStorage
 * @returns {Array<string>} Array of 16 card IDs
 */
function loadDeck() {
    try {
        const stored = localStorage.getItem(DECK_STORAGE_KEY);
        if (stored) {
            const deck = JSON.parse(stored);
            
            // Validate deck
            if (Array.isArray(deck) && deck.length === 16) {
                // Validate all cards exist
                const allValid = deck.every(cardId => cardId in AVAILABLE_CARDS);
                if (allValid) {
                    console.log('✓ Loaded custom deck from storage:', deck);
                    return deck;
                } else {
                    console.warn('Stored deck contains invalid cards, using default');
                }
            } else {
                console.warn('Stored deck invalid format, using default');
            }
        }
    } catch (error) {
        console.error('Error loading deck from storage:', error);
    }
    
    // Return default deck if no valid deck stored
    console.log('Using default deck');
    return [...DEFAULT_DECK]; // Return copy to avoid mutation
}

/**
 * Save the player's deck to localStorage
 * @param {Array<string>} deck - Array of exactly 16 card IDs
 * @returns {boolean} Success status
 */
function saveDeck(deck) {
    // Validate deck
    if (!Array.isArray(deck)) {
        console.error('Deck must be an array');
        return false;
    }
    
    if (deck.length !== 16) {
        console.error(`Deck must contain exactly 16 cards (got ${deck.length})`);
        return false;
    }
    
    // Validate all cards exist
    const invalidCards = deck.filter(cardId => !(cardId in AVAILABLE_CARDS));
    if (invalidCards.length > 0) {
        console.error('Invalid card IDs:', invalidCards);
        return false;
    }
    
    try {
        localStorage.setItem(DECK_STORAGE_KEY, JSON.stringify(deck));
        console.log('✓ Deck saved to storage:', deck);
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
function getDeck() {
    return loadDeck();
}

/**
 * Reset deck to default
 * @returns {boolean} Success status
 */
function resetDeck() {
    return saveDeck(DEFAULT_DECK);
}

/**
 * Check if a deck is currently saved (not using default)
 * @returns {boolean} True if custom deck is saved
 */
function hasCustomDeck() {
    try {
        const stored = localStorage.getItem(DECK_STORAGE_KEY);
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
    
    if (deck.length !== 16) {
        return { valid: false, error: `Deck must contain exactly 16 cards (got ${deck.length})` };
    }
    
    const invalidCards = deck.filter(cardId => !(cardId in AVAILABLE_CARDS));
    if (invalidCards.length > 0) {
        return { valid: false, error: `Invalid card IDs: ${invalidCards.join(', ')}` };
    }
    
    return { valid: true, error: null };
}

// Log that deck manager is loaded
console.log('✓ Deck Manager loaded');
console.log(`  Current deck: ${hasCustomDeck() ? 'Custom' : 'Default'}`);