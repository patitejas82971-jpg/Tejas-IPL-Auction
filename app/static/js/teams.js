/**
 * Team Selection & Squad Management Client Script
 */

class TeamManager {
  constructor(roomId, currentTeamCode) {
    this.roomId = roomId;
    this.selectedTeamCode = currentTeamCode;
    this.initTeamCards();
    this.initSocketEvents();
  }

  initTeamCards() {
    const cards = document.querySelectorAll(".franchise-card:not(.taken)");
    cards.forEach((card) => {
      card.addEventListener("click", () => {
        const code = card.getAttribute("data-team-code");
        this.selectTeam(code);
      });
    });

    const readyBtn = document.getElementById("btnToggleReady");
    if (readyBtn) {
      readyBtn.addEventListener("click", () => {
        if (window.auctionSocket) {
          window.auctionSocket.emit("toggle_ready", { room_id: this.roomId });
        }
      });
    }

    const startBtn = document.getElementById("btnHostStartAuction");
    if (startBtn) {
      startBtn.addEventListener("click", () => {
        if (window.auctionSocket) {
          window.auctionSocket.emit("start_auction", { room_id: this.roomId });
        }
      });
    }
  }

  initSocketEvents() {
    if (!window.auctionSocket) return;

    // Real-time team claiming updates
    window.auctionSocket.on("team_selected", (data) => {
      showToast(`${data.username} selected ${data.team.team_name}!`, "info");
      this.updateFranchiseAvailability(data.available_franchises);
      this.updateParticipantsList(data.teams);
    });

    // Real-time ready status updates
    window.auctionSocket.on("team_ready_updated", (data) => {
      const dot = document.getElementById(`readyDot_${data.team_id}`);
      if (dot) {
        dot.className = `status-dot ${data.is_ready ? "ready" : "not-ready"}`;
      }
      const text = document.getElementById(`readyText_${data.team_id}`);
      if (text) {
        text.textContent = data.is_ready ? "Ready" : "Not Ready";
      }
    });

    // Auction started -> redirect to live arena
    window.auctionSocket.on("auction_started", (data) => {
      showToast("Auction is starting! Entering the auction arena...", "success");
      setTimeout(() => {
        window.location.href = `/auction/${this.roomId}`;
      }, 1000);
    });
  }

  selectTeam(teamCode) {
    if (window.auctionSocket && window.auctionSocket.socket && window.auctionSocket.socket.connected) {
      window.auctionSocket.emit("select_team", {
        room_id: this.roomId,
        team_code: teamCode
      });
    } else {
      // Fallback via REST API
      fetch("/api/teams/select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auction_id: this.roomId, team_code: teamCode })
      })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          showToast(`Selected ${data.team.team_name}!`, "success");
          window.location.reload();
        } else {
          showToast(data.message || "Failed to select team", "danger");
        }
      })
      .catch((err) => {
        showToast("Error selecting team", "danger");
      });
    }
  }

  updateFranchiseAvailability(franchises) {
    if (!franchises) return;
    franchises.forEach((f) => {
      const card = document.querySelector(`.franchise-card[data-team-code="${f.team_code}"]`);
      if (card) {
        if (f.is_taken) {
          card.classList.add("taken");
          const takenLabel = card.querySelector(".taken-by-label");
          if (takenLabel) {
            takenLabel.textContent = `Claimed by ${f.taken_by}`;
          }
        } else {
          card.classList.remove("taken");
          const takenLabel = card.querySelector(".taken-by-label");
          if (takenLabel) {
            takenLabel.textContent = "Available";
          }
        }
      }
    });
  }

  updateParticipantsList(teams) {
    const container = document.getElementById("lobbyParticipantsContainer");
    if (!container || !teams) return;
    
    container.innerHTML = teams.map((t) => `
      <div class="participant-item">
        <div class="d-flex align-items-center gap-2">
          <span class="badge" style="background-color: ${t.primary_color || '#333'}">${t.team_code}</span>
          <div>
            <div class="fw-bold text-white">${t.team_name}</div>
            <div class="text-muted small"><i class="fa-solid fa-user me-1"></i> ${t.owner_name}</div>
          </div>
        </div>
        <div class="d-flex align-items-center gap-2">
          <span class="status-dot ${t.is_ready ? 'ready' : 'not-ready'}" id="readyDot_${t.id}"></span>
          <span class="text-muted small" id="readyText_${t.id}">${t.is_ready ? 'Ready' : 'Not Ready'}</span>
        </div>
      </div>
    `).join("");
  }
}

// Chart.js helper for Squad Role Distribution
function initSquadRoleChart(canvasId, roleCounts) {
  const ctx = document.getElementById(canvasId);
  if (!ctx || typeof Chart === "undefined") return;

  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Batsmen", "Bowlers", "All-rounders", "Wicketkeepers"],
      datasets: [{
        data: [
          roleCounts.Batsman || 0,
          roleCounts.Bowler || 0,
          roleCounts["All-rounder"] || 0,
          roleCounts.Wicketkeeper || 0
        ],
        backgroundColor: ["#60A5FA", "#F87171", "#C084FC", "#34D399"],
        borderColor: "#071A36",
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: "#F1F5F9", font: { family: "Inter", size: 12 } }
        }
      },
      cutout: "65%"
    }
  });
}

window.TeamManager = TeamManager;
window.initSquadRoleChart = initSquadRoleChart;
