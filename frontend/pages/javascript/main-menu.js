const music = document.getElementById('menuMusic');
const clickOn = document.getElementById('menuClickOn');
const clickOff = document.getElementById('menuClickOff');

// Start background music on first user interaction
function startMusic() {
  if (music.paused) {
    music.volume = 0.3;
    music.play().catch(err => console.log('Autoplay prevented:', err));
  }
}
document.addEventListener('click', startMusic, { once: true });
document.addEventListener('keydown', startMusic, { once: true });

// Apply sounds to each button
document.querySelectorAll('.menu-btn').forEach(btn => {

  // Play "click on" when pressing down, nothing else
  btn.addEventListener('mousedown', () => {
    clickOn.currentTime = 0;
    clickOn.volume = 0.7;
    clickOn.play().catch(() => {});
  });

  // Play "click off" when releasing the mouse, add button logic here
  btn.addEventListener('mouseup', () => {
    clickOff.currentTime = 0;
    clickOff.volume = 0.7;
    clickOff.play().catch(() => {});
  });
});