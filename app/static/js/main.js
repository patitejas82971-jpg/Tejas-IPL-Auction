/**
 * IPL Auction Simulator - Core Client Script
 * Includes Web Audio API synthesizer for reliable sound effects & utilities
 */

// Sound Synthesizer using Web Audio API
class AuctionAudio {
  constructor() {
    this.ctx = null;
    this.isMuted = localStorage.getItem("ipl_auction_muted") === "true";
    this.initAudioContext();
  }

  initAudioContext() {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.ctx = new AudioContext();
      }
    } catch (e) {
      console.warn("Web Audio API not supported:", e);
    }
  }

  resume() {
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume();
    }
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    localStorage.setItem("ipl_auction_muted", this.isMuted);
    this.updateMuteButtonUI();
    return this.isMuted;
  }

  updateMuteButtonUI() {
    const btn = document.getElementById("soundToggleBtn");
    if (!btn) return;
    if (this.isMuted) {
      btn.innerHTML = '<i class="fa-solid fa-volume-xmark"></i>';
      btn.title = "Unmute Sounds";
      btn.classList.add("text-danger");
    } else {
      btn.innerHTML = '<i class="fa-solid fa-volume-high"></i>';
      btn.title = "Mute Sounds";
      btn.classList.remove("text-danger");
    }
  }

  // Sound 1: Bid Placed Ding
  playBidSound() {
    if (window.AndroidBridge && typeof window.AndroidBridge.vibrate === 'function') {
      try { window.AndroidBridge.vibrate(35); } catch (e) {}
    }
    if (this.isMuted || !this.ctx) return;
    this.resume();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(587.33, this.ctx.currentTime); // D5
    osc.frequency.exponentialRampToValueAtTime(880, this.ctx.currentTime + 0.15); // A5
    gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.25);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.25);
  }

  // Sound 2: Player Sold (Gavel Knock & Celebration Chime)
  playSoldSound() {
    if (window.AndroidBridge && typeof window.AndroidBridge.onPlayerSold === 'function') {
      try { window.AndroidBridge.onPlayerSold("", ""); } catch (e) {}
    }
    if (this.isMuted || !this.ctx) return;
    this.resume();
    // Gavel knock
    const osc1 = this.ctx.createOscillator();
    const gain1 = this.ctx.createGain();
    osc1.type = "triangle";
    osc1.frequency.setValueAtTime(140, this.ctx.currentTime);
    osc1.frequency.exponentialRampToValueAtTime(40, this.ctx.currentTime + 0.1);
    gain1.gain.setValueAtTime(0.5, this.ctx.currentTime);
    gain1.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.15);
    osc1.connect(gain1);
    gain1.connect(this.ctx.destination);
    osc1.start();
    osc1.stop(this.ctx.currentTime + 0.15);

    // Chime
    setTimeout(() => {
      if (this.isMuted || !this.ctx) return;
      const osc2 = this.ctx.createOscillator();
      const gain2 = this.ctx.createGain();
      osc2.type = "sine";
      osc2.frequency.setValueAtTime(523.25, this.ctx.currentTime); // C5
      osc2.frequency.setValueAtTime(659.25, this.ctx.currentTime + 0.1); // E5
      osc2.frequency.setValueAtTime(783.99, this.ctx.currentTime + 0.2); // G5
      osc2.frequency.setValueAtTime(1046.50, this.ctx.currentTime + 0.3); // C6
      gain2.gain.setValueAtTime(0.25, this.ctx.currentTime);
      gain2.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.6);
      osc2.connect(gain2);
      gain2.connect(this.ctx.destination);
      osc2.start();
      osc2.stop(this.ctx.currentTime + 0.6);
    }, 120);
  }

  // Sound 3: Player Unsold (Buzzer)
  playUnsoldSound() {
    if (this.isMuted || !this.ctx) return;
    this.resume();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(150, this.ctx.currentTime);
    osc.frequency.setValueAtTime(130, this.ctx.currentTime + 0.15);
    gain.gain.setValueAtTime(0.2, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.4);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.4);
  }

  // Sound 4: New Player Fanfare Whistle
  playNewPlayerSound() {
    if (this.isMuted || !this.ctx) return;
    this.resume();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(440, this.ctx.currentTime); // A4
    osc.frequency.setValueAtTime(554.37, this.ctx.currentTime + 0.1); // C#5
    osc.frequency.setValueAtTime(659.25, this.ctx.currentTime + 0.2); // E5
    gain.gain.setValueAtTime(0.25, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.45);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.45);
  }

  // Sound 5: Timer warning tick (last 5s)
  playTickSound() {
    if (this.isMuted || !this.ctx) return;
    this.resume();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(1200, this.ctx.currentTime);
    gain.gain.setValueAtTime(0.15, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.05);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.05);
  }
}

// Global audio singleton
window.auctionAudio = new AuctionAudio();

// Format INR currency
function formatINR(amount) {
  if (amount === undefined || amount === null) return "₹0";
  const num = Number(amount);
  if (num >= 10000000) {
    const cr = (num / 10000000).toFixed(2).replace(/\.?0+$/, "");
    return `₹${cr} Cr`;
  } else if (num >= 100000) {
    const lakh = (num / 100000).toFixed(2).replace(/\.?0+$/, "");
    return `₹${lakh} Lakh`;
  }
  return `₹${num.toLocaleString("en-IN")}`;
}

// Copy to Clipboard
function copyToClipboard(text, successMessage = "Copied to clipboard!") {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(successMessage, "success");
    }).catch(() => {
      fallbackCopyText(text, successMessage);
    });
  } else {
    fallbackCopyText(text, successMessage);
  }
}

function fallbackCopyText(text, successMessage) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  try {
    document.execCommand("copy");
    showToast(successMessage, "success");
  } catch (err) {
    showToast("Failed to copy", "danger");
  }
  document.body.removeChild(textArea);
}

// Toast notification helper
function showToast(message, type = "info") {
  if (window.AndroidBridge && typeof window.AndroidBridge.showToast === 'function') {
    try { window.AndroidBridge.showToast(message); } catch (e) {}
  }
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toastEl = document.createElement("div");
  toastEl.className = `alert alert-${type === "error" ? "danger" : type} alert-dismissible fade show alert-ipl shadow-lg mb-2`;
  toastEl.style.minWidth = "280px";
  toastEl.role = "alert";
  toastEl.innerHTML = `
    <div class="d-flex align-items-center gap-2">
      <i class="fa-solid ${type === 'success' ? 'fa-circle-check text-success' : type === 'danger' ? 'fa-triangle-exclamation text-danger' : 'fa-circle-info text-info'}"></i>
      <div>${message}</div>
    </div>
    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
  container.appendChild(toastEl);

  setTimeout(() => {
    toastEl.classList.remove("show");
    setTimeout(() => toastEl.remove(), 250);
  }, 4000);
}

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  window.auctionAudio.updateMuteButtonUI();
  
  const soundBtn = document.getElementById("soundToggleBtn");
  if (soundBtn) {
    soundBtn.addEventListener("click", () => {
      window.auctionAudio.toggleMute();
    });
  }

  // Resume Web Audio on first user interaction anywhere
  document.addEventListener("click", () => {
    window.auctionAudio.resume();
  }, { once: true });
});

// Lightweight Celebration Confetti Particle Engine
window.launchConfetti = function() {
  const canvas = document.getElementById("confettiCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const colors = ["#F5B841", "#00E676", "#FF7A00", "#00D2FF", "#FFFFFF", "#EC1C24"];
  const particles = [];
  const particleCount = 80;

  for (let i = 0; i < particleCount; i++) {
    particles.push({
      x: canvas.width / 2 + (Math.random() - 0.5) * 200,
      y: canvas.height * 0.4 + (Math.random() - 0.5) * 100,
      w: Math.random() * 10 + 6,
      h: Math.random() * 8 + 4,
      vx: (Math.random() - 0.5) * 16,
      vy: Math.random() * -14 - 4,
      color: colors[Math.floor(Math.random() * colors.length)],
      rotation: Math.random() * 360,
      vRotation: (Math.random() - 0.5) * 10,
      opacity: 1
    });
  }

  let animFrameId = null;
  const startTime = Date.now();

  function renderConfetti() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const elapsed = Date.now() - startTime;

    particles.forEach((p) => {
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.45; // gravity
      p.vx *= 0.98; // air resistance
      p.rotation += p.vRotation;
      if (elapsed > 1800) {
        p.opacity = Math.max(0, p.opacity - 0.03);
      }

      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate((p.rotation * Math.PI) / 180);
      ctx.globalAlpha = p.opacity;
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    });

    if (elapsed < 2800) {
      animFrameId = requestAnimationFrame(renderConfetti);
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      cancelAnimationFrame(animFrameId);
    }
  }

  renderConfetti();
};

