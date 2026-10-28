/**
 * IPL Live Auction Controller
 * Real-time bidding, state management, audio cues, and AI Assistant integration
 */

class LiveAuctionManager {
  constructor(config) {
    this.roomId = config.roomId;
    this.userTeamId = config.userTeamId;
    this.userTeamCode = config.userTeamCode;
    this.username = config.username;
    this.isHost = config.isHost;

    this.timer = typeof AuctionTimer !== "undefined" ? new AuctionTimer("auctionTimerCircle", "timerDigits") : null;
    this.currentPlayer = null;
    this.currentBid = 0;
    this.nextBidAmount = 0;
    this.highestTeamId = null;

    this.initElements();
    this.initSocketEvents();
    this.initUIListeners();
  }

  initElements() {
    this.playerNameEl = document.getElementById("spotlightPlayerName");
    this.playerRoleEl = document.getElementById("spotlightPlayerRole");
    this.playerCountryEl = document.getElementById("spotlightPlayerCountry");
    this.playerRatingEl = document.getElementById("spotlightPlayerRating");
    this.playerAvatarEl = document.getElementById("spotlightPlayerAvatar");
    this.playerStyleEl = document.getElementById("spotlightPlayerStyle");
    this.basePriceEl = document.getElementById("spotlightBasePrice");
    this.currentBidEl = document.getElementById("currentBidDisplay");
    this.highestBidderEl = document.getElementById("highestBidderDisplay");
    this.btnBidMain = document.getElementById("btnBidMain");
    this.bidAmountLabel = document.getElementById("bidAmountLabel");
    this.feedContainer = document.getElementById("liveFeedContainer");
    this.soldOverlay = document.getElementById("soldOverlay");
    this.soldStamp = document.getElementById("soldStamp");
    this.soldDetails = document.getElementById("soldDetails");

    // Pool and Set Elements
    this.playerPoolEl = document.getElementById("spotlightPlayerPool");
    this.playerSetEl = document.getElementById("spotlightPlayerSetText");
    this.currentPoolBadge = document.getElementById("currentPoolBadge");
    this.currentSetBadge = document.getElementById("currentSetBadge");

    // AI Drawer Elements
    this.aiLoadingEl = document.getElementById("aiLoading");
    this.aiContentEl = document.getElementById("aiContent");
    this.aiNoticeEl = document.getElementById("aiNotice");
    this.aiRecommendedRangeEl = document.getElementById("aiRecommendedRange");
    this.aiVerdictEl = document.getElementById("aiVerdict");
    this.aiStrengthsList = document.getElementById("aiStrengthsList");
    this.aiSquadFitEl = document.getElementById("aiSquadFit");
  }

  initSocketEvents() {
    window.auctionSocket.connect(this.roomId, this.username);

    // Initial synchronized state
    window.auctionSocket.on("auction_state", (state) => {
      this.handleAuctionState(state);
    });

    // New Player Announced
    window.auctionSocket.on("player_announced", (data) => {
      this.handlePlayerAnnounced(data);
    });

    // Bid Placed
    window.auctionSocket.on("bid_updated", (data) => {
      this.handleBidUpdated(data);
    });

    // Server Timer Tick (if any)
    window.auctionSocket.on("timer_updated", (data) => {
      if (this.timer) {
        this.timer.updateSeconds(data.seconds_left);
      }
    });

    // Player Sold
    window.auctionSocket.on("player_sold", (data) => {
      this.handlePlayerSold(data);
    });

    // Player Unsold
    window.auctionSocket.on("player_unsold", (data) => {
      this.handlePlayerUnsold(data);
    });

    // Auction Paused / Resumed
    window.auctionSocket.on("auction_paused", (data) => {
      this.timer.pause();
      this.addFeedItem("Auction PAUSED by Host", "warning");
      showToast("Auction has been paused by the host.", "warning");
    });

    window.auctionSocket.on("auction_resumed", (data) => {
      this.timer.resume();
      this.addFeedItem("Auction RESUMED", "info");
      showToast("Auction resumed!", "info");
    });

    // Auction Completed
    window.auctionSocket.on("auction_ended", (data) => {
      showToast("Auction complete! Loading final results...", "success");
      setTimeout(() => {
        window.location.href = `/auction/${this.roomId}/results`;
      }, 2500);
    });
  }

  initUIListeners() {
    // Primary Bid Now button
    if (this.btnBidMain) {
      this.btnBidMain.addEventListener("click", () => {
        this.placeBid(this.nextBidAmount);
      });
    }

    // Quick increment buttons (+10L, +25L, +50L, +1Cr)
    document.querySelectorAll(".btn-quick-bid").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const increment = Number(btn.getAttribute("data-increment") || 0);
        const amount = (this.currentBid > 0 ? this.currentBid : (this.currentPlayer ? this.currentPlayer.base_price : 0)) + increment;
        this.placeBid(amount);
      });
    });

    // AI Strategy Assistant Button
    const aiBtn = document.getElementById("btnAiAssistant");
    if (aiBtn) {
      aiBtn.addEventListener("click", () => {
        this.fetchAiPlayerAnalysis();
      });
    }

    // Host Auctioneer Gavel & Skip Controls
    const triggerHammer = () => {
      if (this.currentBid === 0) {
        if (!confirm("No bids have been placed on this player yet. Strike hammer and mark as Unsold?")) {
          return;
        }
      }
      window.auctionSocket.emit("host_hammer", { room_id: this.roomId });
    };

    const triggerUnsold = () => {
      if (confirm("Mark this player as Unsold and advance?")) {
        window.auctionSocket.emit("host_unsold", { room_id: this.roomId });
      }
    };

    const btnHammer = document.getElementById("btnHostHammer");
    if (btnHammer) btnHammer.addEventListener("click", triggerHammer);

    const btnStageHammer = document.getElementById("btnStageHammer");
    if (btnStageHammer) btnStageHammer.addEventListener("click", triggerHammer);

    const btnUnsold = document.getElementById("btnHostUnsold");
    if (btnUnsold) btnUnsold.addEventListener("click", triggerUnsold);

    const btnStageUnsold = document.getElementById("btnStageUnsold");
    if (btnStageUnsold) btnStageUnsold.addEventListener("click", triggerUnsold);

    const btnSkip = document.getElementById("btnHostSkip");
    if (btnSkip) {
      btnSkip.addEventListener("click", () => {
        if (confirm("Are you sure you want to skip this player?")) {
          window.auctionSocket.emit("skip_player", { room_id: this.roomId });
        }
      });
    }

    // Host Jump Set Listeners
    document.querySelectorAll(".btn-jump-set").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const setName = btn.getAttribute("data-set-name");
        if (!confirm(`Advance auction queue to start ${setName} next?`)) return;
        try {
          const res = await fetch(`/api/auction/${this.roomId}/jump-set`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ set_name: setName })
          });
          const result = await res.json();
          if (result.success) {
            showToast(result.message, "success");
            const modalEl = document.getElementById("poolsModal");
            if (modalEl && window.bootstrap) {
              const modal = bootstrap.Modal.getInstance(modalEl);
              if (modal) modal.hide();
            }
          } else {
            showToast(result.message || "Failed to jump set", "danger");
          }
        } catch (err) {
          showToast("Network error jumping set", "danger");
        }
      });
    });
  }

  placeBid(amount = null) {
    if (!this.userTeamId) {
      showToast("You have not selected a franchise to place bids with!", "warning");
      return;
    }
    window.auctionSocket.emit("place_bid", {
      room_id: this.roomId,
      amount: amount
    });
  }

  handleAuctionState(state) {
    if (state.current_player) {
      this.currentPlayer = state.current_player;
      this.updatePlayerUI(state.current_player);
    }
    this.currentBid = state.current_highest_bid || 0;
    this.highestTeamId = state.current_highest_team_id;
    this.updateBidUI(this.currentBid, state.highest_bidding_team);
    this.calculateNextBid();
  }

  handlePlayerAnnounced(data) {
    if (this.soldOverlay) {
      this.soldOverlay.classList.add("d-none");
    }
    this.currentPlayer = data.player;
    this.currentBid = 0;
    this.highestTeamId = null;

    this.updatePlayerUI(data.player);
    this.updateBidUI(0, null);
    this.calculateNextBid();
    if (this.timer && data.timer_duration) {
      this.timer.setDuration(data.timer_duration);
      this.timer.updateSeconds(data.timer_duration);
    }

    if (window.auctionAudio) {
      window.auctionAudio.playNewPlayerSound();
    }

    this.addFeedItem(`Up for Auction: ${data.player.name} (${data.player.role}, Base: ${data.player.base_price_formatted})`, "info");
  }

  handleBidUpdated(data) {
    this.currentBid = data.amount;
    this.highestTeamId = data.team_id;
    this.nextBidAmount = data.next_bid;

    this.updateBidUI(data.amount, {
      team_name: data.team_name,
      team_code: data.team_code,
      primary_color: data.primary_color
    });

    if (this.bidAmountLabel) {
      this.bidAmountLabel.textContent = data.next_bid_formatted;
    }

    if (window.auctionAudio) {
      window.auctionAudio.playBidSound();
    }

    this.addFeedItem(`${data.team_code} bids ${data.amount_formatted}!`, "bid", data.primary_color);
  }

  handlePlayerSold(data) {
    if (window.auctionAudio) {
      window.auctionAudio.playSoldSound();
    }

    // Trigger Sold Stamp Overlay
    if (this.soldOverlay && this.soldStamp && this.soldDetails) {
      this.soldStamp.className = "sold-stamp";
      this.soldStamp.textContent = "SOLD";
      this.soldDetails.innerHTML = `
        <h3 class="text-white mb-2">${data.player_name}</h3>
        <div class="h4" style="color: ${data.primary_color || 'var(--gold)'}; font-weight: 800;">
          <i class="fa-solid fa-crown me-1"></i> ${data.team_name}
        </div>
        <div class="badge bg-success fs-5 mt-2 px-3 py-2">
          ${data.price_formatted}
        </div>
      `;
      this.soldOverlay.classList.remove("d-none");
    }

    this.addFeedItem(`${data.player_name} SOLD to ${data.team_name} for ${data.price_formatted}!`, "sold");

    // Update remaining budget badge if this is user's team
    if (this.userTeamId && Number(data.team_id) === Number(this.userTeamId)) {
      const budgetBadge = document.getElementById("myTeamRemainingBudget");
      if (budgetBadge) {
        budgetBadge.textContent = data.team_remaining_budget_formatted;
      }
      const squadCountBadge = document.getElementById("myTeamSquadCount");
      if (squadCountBadge) {
        squadCountBadge.textContent = data.team_squad_count;
      }
    }
  }

  handlePlayerUnsold(data) {
    if (window.auctionAudio) {
      window.auctionAudio.playUnsoldSound();
    }

    // Trigger Unsold Stamp Overlay
    if (this.soldOverlay && this.soldStamp && this.soldDetails) {
      this.soldStamp.className = "unsold-stamp";
      this.soldStamp.textContent = "UNSOLD";
      this.soldDetails.innerHTML = `
        <h3 class="text-white mb-2">${data.player_name}</h3>
        <div class="text-muted fs-5">No bids received above base price (${data.base_price_formatted})</div>
      `;
      this.soldOverlay.classList.remove("d-none");
    }

    this.addFeedItem(`${data.player_name} passed UNSOLD`, "unsold");
  }

  updatePlayerUI(player) {
    if (!player) return;
    if (this.playerNameEl) this.playerNameEl.textContent = player.name;
    if (this.playerRoleEl) {
      this.playerRoleEl.textContent = player.role;
      this.playerRoleEl.className = `badge badge-role badge-${player.role.toLowerCase().replace(/[^a-z]/g, "")}`;
    }
    if (this.playerCountryEl) {
      this.playerCountryEl.innerHTML = player.is_overseas ? 
        `<span class="badge badge-overseas"><i class="fa-solid fa-earth-americas me-1"></i> ${player.country} (Overseas)</span>` : 
        `<span class="badge badge-gold"><i class="fa-solid fa-flag me-1"></i> ${player.country}</span>`;
    }
    if (this.playerRatingEl) this.playerRatingEl.textContent = player.rating;
    if (this.playerAvatarEl) this.playerAvatarEl.src = player.image_url;
    if (this.playerStyleEl) {
      this.playerStyleEl.textContent = `${player.batting_style} | ${player.bowling_style}`;
    }
    if (this.basePriceEl) this.basePriceEl.textContent = player.base_price_formatted;

    // Dynamic Pool Badge update
    if (this.playerPoolEl) {
      const isMarquee = player.pool === "Marquee" || player.is_marquee;
      const isUncapped = player.pool === "Uncapped" || player.is_uncapped;
      if (isMarquee) {
        this.playerPoolEl.innerHTML = `<span class="badge badge-pool badge-marquee"><i class="fa-solid fa-crown me-1"></i> MARQUEE PLAYER</span>`;
      } else if (isUncapped) {
        this.playerPoolEl.innerHTML = `<span class="badge badge-pool badge-uncapped"><i class="fa-solid fa-seedling me-1"></i> UNCAPPED PLAYER</span>`;
      } else {
        this.playerPoolEl.innerHTML = `<span class="badge badge-pool badge-capped"><i class="fa-solid fa-star me-1"></i> CAPPED PLAYER</span>`;
      }
    }

    // Set text updates
    if (this.playerSetEl && player.set_name) {
      this.playerSetEl.textContent = player.set_name;
    }
    if (this.currentPoolBadge && player.pool) {
      this.currentPoolBadge.textContent = player.pool;
    }
    if (this.currentSetBadge && player.set_name) {
      this.currentSetBadge.textContent = player.set_name;
    }
  }

  updateBidUI(amount, team) {
    if (this.currentBidEl) {
      this.currentBidEl.textContent = amount > 0 ? formatINR(amount) : "₹0";
      this.currentBidEl.classList.remove("anim-bid-pop");
      void this.currentBidEl.offsetWidth; // trigger reflow
      this.currentBidEl.classList.add("anim-bid-pop");
    }

    if (this.highestBidderEl) {
      if (team && amount > 0) {
        this.highestBidderEl.innerHTML = `
          <div class="highest-bidder-pill" style="border-color: ${team.primary_color || 'var(--gold)'}; color: #FFFFFF;">
            <span class="badge me-1" style="background-color: ${team.primary_color || '#333'}">${team.team_code}</span>
            <span>${team.team_name}</span>
          </div>
        `;
      } else {
        this.highestBidderEl.innerHTML = `
          <div class="text-muted fs-6"><i class="fa-regular fa-clock me-1"></i> Waiting for opening bid...</div>
        `;
      }
    }

    // Disable bid button if user is already highest bidder
    if (this.btnBidMain && this.userTeamId) {
      if (this.highestTeamId && Number(this.highestTeamId) === Number(this.userTeamId)) {
        this.btnBidMain.disabled = true;
        this.btnBidMain.innerHTML = '<i class="fa-solid fa-check-double me-2"></i> Highest Bidder!';
      } else {
        this.btnBidMain.disabled = false;
        this.btnBidMain.innerHTML = `<i class="fa-solid fa-gavel me-2"></i> Bid Now (${this.bidAmountLabel ? this.bidAmountLabel.textContent : ''})`;
      }
    }
  }

  calculateNextBid() {
    if (!this.currentPlayer) return;
    let next = 0;
    if (this.currentBid <= 0) {
      next = this.currentPlayer.base_price;
    } else if (this.currentBid < 10000000) {
      next = this.currentBid + 1000000;
    } else if (this.currentBid < 20000000) {
      next = this.currentBid + 2000000;
    } else if (this.currentBid < 50000000) {
      next = this.currentBid + 2500000;
    } else if (this.currentBid < 100000000) {
      next = this.currentBid + 5000000;
    } else {
      next = this.currentBid + 10000000;
    }
    this.nextBidAmount = next;
    if (this.bidAmountLabel) {
      this.bidAmountLabel.textContent = formatINR(next);
    }
    if (this.btnBidMain && (!this.highestTeamId || Number(this.highestTeamId) !== Number(this.userTeamId))) {
      this.btnBidMain.innerHTML = `<i class="fa-solid fa-gavel me-2"></i> Bid Now (${formatINR(next)})`;
    }
  }

  addFeedItem(text, type = "info", highlightColor = null) {
    if (!this.feedContainer) return;
    const item = document.createElement("div");
    item.className = `feed-item ${type}`;
    if (highlightColor) {
      item.style.borderLeftColor = highlightColor;
    }
    item.innerHTML = `
      <div class="d-flex justify-content-between align-items-center">
        <span>${text}</span>
        <span class="text-muted small">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
      </div>
    `;
    this.feedContainer.prepend(item);
  }

  // Fetch AI Player Analysis (Gemini Assistant)
  async fetchAiPlayerAnalysis() {
    if (!this.currentPlayer) return;
    if (this.aiLoadingEl) this.aiLoadingEl.classList.remove("d-none");
    if (this.aiContentEl) this.aiContentEl.classList.add("d-none");

    const modal = new bootstrap.Modal(document.getElementById("aiModal"));
    modal.show();

    try {
      const res = await fetch("/api/ai/player-analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player_id: this.currentPlayer.id,
          player: this.currentPlayer
        })
      });
      const data = await res.json();
      if (data.success && data.analysis) {
        this.renderAiAnalysis(data.analysis);
      }
    } catch (e) {
      console.warn("AI analysis request error:", e);
      if (this.aiNoticeEl) {
        this.aiNoticeEl.textContent = "AI insights are temporarily unavailable. You can continue your auction normally.";
      }
    } finally {
      if (this.aiLoadingEl) this.aiLoadingEl.classList.add("d-none");
      if (this.aiContentEl) this.aiContentEl.classList.remove("d-none");
    }
  }

  renderAiAnalysis(analysis) {
    if (this.aiNoticeEl) {
      this.aiNoticeEl.textContent = analysis.notice || "";
    }
    if (this.aiRecommendedRangeEl) {
      this.aiRecommendedRangeEl.textContent = analysis.recommended_bid_range || "N/A";
    }
    if (this.aiVerdictEl) {
      this.aiVerdictEl.textContent = analysis.verdict || "";
    }
    if (this.aiSquadFitEl) {
      this.aiSquadFitEl.textContent = analysis.squad_fit || "";
    }
    if (this.aiStrengthsList && Array.isArray(analysis.strengths)) {
      this.aiStrengthsList.innerHTML = analysis.strengths
        .map((s) => `<li><i class="fa-solid fa-check text-success me-2"></i>${s}</li>`)
        .join("");
    }
  }
}

window.LiveAuctionManager = LiveAuctionManager;
