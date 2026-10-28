/**
 * Authoritative Live Auction Timer Controller
 */

class AuctionTimer {
  constructor(circleElementId, digitsElementId) {
    this.circleEl = document.getElementById(circleElementId);
    this.digitsEl = document.getElementById(digitsElementId);
    this.totalDuration = 30;
    this.secondsRemaining = 30;
    this.timerInterval = null;
    this.isPaused = false;
  }

  setDuration(duration) {
    this.totalDuration = Math.max(5, duration);
  }

  updateSeconds(seconds) {
    this.secondsRemaining = Math.max(0, seconds);
    this.render();

    // Play warning tick on last 5 seconds
    if (this.secondsRemaining > 0 && this.secondsRemaining <= 5 && !this.isPaused) {
      if (window.auctionAudio) {
        window.auctionAudio.playTickSound();
      }
    }
  }

  render() {
    if (this.digitsEl) {
      this.digitsEl.textContent = this.secondsRemaining;
    }

    if (this.circleEl) {
      if (this.secondsRemaining <= 5 && this.secondsRemaining > 0) {
        this.circleEl.classList.add("warning");
      } else {
        this.circleEl.classList.remove("warning");
      }
    }
  }

  pause() {
    this.isPaused = true;
    if (this.circleEl) {
      this.circleEl.classList.remove("warning");
    }
  }

  resume() {
    this.isPaused = false;
  }
}

window.AuctionTimer = AuctionTimer;
