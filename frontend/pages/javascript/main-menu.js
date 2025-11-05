// Button logging
document.querySelectorAll('.menu-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    console.log(`${btn.id} clicked`);
    // Later: add logic for navigation here
  });
});

// Background music
const music = document.getElementById('menuMusic');

function startMusic() {
  if (music.paused) {
    music.volume = 0.4; // Adjust to taste (0.0–1.0)
    music.play().catch(err => console.log('Autoplay prevented:', err));
  }
}

// Wait for *first* user interaction before playing
document.addEventListener('click', startMusic, { once: true });
document.addEventListener('keydown', startMusic, { once: true });
