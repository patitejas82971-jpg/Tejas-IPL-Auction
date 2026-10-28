/**
 * Socket.IO & REST Hybrid Connection Manager for IPL Auction Simulator
 * Seamlessly provides WebSocket real-time bidding, with automatic fallback
 * to HTTP REST polling for serverless environments (e.g. Vercel) or restricted networks.
 */

class AuctionSocket {
  constructor() {
    this.socket = null;
    this.roomId = null;
    this.username = "Participant";
    this.handlers = {};
    this.isPollingFallback = false;
    this.pollingInterval = null;
    this.lastState = null;
    this.connectAttempts = 0;
  }

  connect(roomId, username = "Participant") {
    this.roomId = roomId;
    this.username = username;

    if (typeof io === "undefined") {
      console.warn("Socket.io library not loaded. Falling back to REST polling.");
      this.activateRestFallback();
      return;
    }

    try {
      this.socket = io({
        transports: ["websocket", "polling"],
        reconnection: true,
        reconnectionAttempts: 4,
        reconnectionDelay: 1000,
        timeout: 4000
      });

      this.socket.on("connect", () => {
        console.log("Connected to auction WebSocket server with id:", this.socket.id);
        this.stopRestFallback();
        this.joinRoom(this.roomId, username);
      });

      this.socket.on("connect_error", (err) => {
        console.warn("Socket.io connect error:", err.message);
        this.connectAttempts++;
        if (this.connectAttempts >= 2 && !this.isPollingFallback) {
          console.info("Switching to HTTP REST polling mode for live bidding (Serverless/Vercel support).");
          this.activateRestFallback();
        }
      });

      this.socket.on("disconnect", (reason) => {
        console.warn("Socket disconnected:", reason);
        if (reason === "io server disconnect" || reason === "transport close") {
          this.activateRestFallback();
        }
      });

      this.socket.on("reconnect", () => {
        console.log("Socket reconnected!");
        this.stopRestFallback();
        if (typeof showToast === "function") {
          showToast("Connected via WebSocket!", "success");
        }
        this.joinRoom(this.roomId, username);
        this.socket.emit("request_auction_state", { room_id: this.roomId });
      });

      this.socket.on("error_message", (data) => {
        console.error("Socket error received:", data);
        if (typeof showToast === "function") {
          showToast(data.message || "An error occurred", "danger");
        }
      });

      // Forward registered handlers to the socket instance
      Object.keys(this.handlers).forEach((event) => {
        this.handlers[event].forEach((cb) => {
          this.socket.on(event, cb);
        });
      });

      // Safety timeout: if after 3.5s socket still isn't connected, activate REST polling
      setTimeout(() => {
        if (!this.socket || !this.socket.connected) {
          this.activateRestFallback();
        }
      }, 3500);

    } catch (e) {
      console.warn("Socket initialization error:", e);
      this.activateRestFallback();
    }
  }

  joinRoom(roomId, username) {
    if (this.socket && this.socket.connected) {
      this.socket.emit("join_room", { room_id: roomId, username: username });
    }
  }

  leaveRoom() {
    this.stopRestFallback();
    if (this.socket && this.socket.connected && this.roomId) {
      this.socket.emit("leave_room", { room_id: this.roomId });
    }
  }

  on(event, callback) {
    if (!this.handlers[event]) {
      this.handlers[event] = [];
    }
    this.handlers[event].push(callback);

    if (this.socket) {
      this.socket.on(event, callback);
    }
  }

  trigger(event, data) {
    const list = this.handlers[event] || [];
    list.forEach((cb) => {
      try {
        cb(data);
      } catch (err) {
        console.error(`Error in handler for ${event}:`, err);
      }
    });
  }

  emit(event, data) {
    // If socket is connected, emit through WebSocket
    if (this.socket && this.socket.connected) {
      this.socket.emit(event, data);
      return;
    }

    // Fallback: translate Socket.IO events to REST API endpoints
    this.handleRestEmit(event, data);
  }

  handleRestEmit(event, data) {
    const roomId = this.roomId || (data && data.room_id);
    if (!roomId) return;

    if (event === "place_bid") {
      fetch(`/api/auctions/${roomId}/bid`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount: data.amount })
      })
      .then((res) => res.json())
      .then((res) => {
        if (!res.success) {
          if (typeof showToast === "function") showToast(res.message, "danger");
        } else {
          this.trigger("bid_updated", res.bid);
        }
      })
      .catch((err) => console.error("REST bid error:", err));
    } else if (event === "host_hammer") {
      fetch(`/api/auctions/${roomId}/hammer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      })
      .then((res) => res.json())
      .then((res) => {
        if (res.success) {
          const evt = res.is_sold ? "player_sold" : "player_unsold";
          this.trigger(evt, res.result);
        }
      });
    } else if (event === "host_unsold") {
      fetch(`/api/auctions/${roomId}/unsold`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      })
      .then((res) => res.json())
      .then((res) => {
        if (res.success) this.trigger("player_unsold", res.result);
      });
    } else if (event === "host_skip" || event === "skip_player") {
      fetch(`/api/auctions/${roomId}/skip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
    } else if (event === "request_auction_state") {
      this.pollStateOnce();
    }
  }

  activateRestFallback() {
    if (this.isPollingFallback) return;
    this.isPollingFallback = true;
    console.info("REST Live Polling active (1.5s intervals)");

    this.pollStateOnce();
    if (!this.pollingInterval) {
      this.pollingInterval = setInterval(() => {
        this.pollStateOnce();
      }, 1500);
    }
  }

  stopRestFallback() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
    this.isPollingFallback = false;
  }

  pollStateOnce() {
    if (!this.roomId) return;

    fetch(`/api/auctions/${this.roomId}/state`)
      .then((res) => res.json())
      .then((data) => {
        if (!data || !data.success) return;

        const isFirst = !this.lastState;
        const prev = this.lastState || {};
        this.lastState = data;

        // On first fetch, trigger auction_state
        if (isFirst) {
          this.trigger("auction_state", {
            room_id: data.room_id,
            status: data.status,
            current_player: data.current_player,
            current_highest_bid: data.current_highest_bid,
            current_highest_bid_formatted: data.current_highest_bid_formatted,
            highest_bidding_team: data.current_highest_team,
            next_bid: data.next_bid,
            next_bid_formatted: data.next_bid_formatted,
            seconds_left: data.seconds_left,
            teams: data.teams,
            recent_bids: data.recent_bids
          });
          return;
        }

        // Detect player change
        const prevPlayerId = prev.current_player ? prev.current_player.id : null;
        const curPlayerId = data.current_player ? data.current_player.id : null;
        if (curPlayerId && curPlayerId !== prevPlayerId) {
          this.trigger("player_announced", {
            player: data.current_player,
            base_price: data.current_player.base_price,
            base_price_formatted: formatINR(data.current_player.base_price),
            timer_duration: data.seconds_left || 30
          });
        }

        // Detect bid change
        if (data.current_highest_bid !== prev.current_highest_bid && data.current_highest_bid > 0) {
          const topBid = (data.recent_bids && data.recent_bids[0]) || {};
          this.trigger("bid_updated", {
            auction_id: data.room_id,
            player_id: curPlayerId,
            amount: data.current_highest_bid,
            amount_formatted: data.current_highest_bid_formatted,
            next_bid: data.next_bid,
            next_bid_formatted: data.next_bid_formatted,
            team_id: data.current_highest_team ? data.current_highest_team.id : null,
            team_code: data.current_highest_team ? data.current_highest_team.team_code : "",
            team_name: data.current_highest_team ? data.current_highest_team.team_name : "",
            primary_color: data.current_highest_team ? data.current_highest_team.primary_color : "#F5B841",
            timestamp: topBid.created_at ? topBid.created_at.substring(11, 19) : ""
          });
        }

        // Always update timer
        if (data.seconds_left !== undefined) {
          this.trigger("timer_updated", { seconds_left: data.seconds_left });
        }

        // Detect auction completion
        if (data.status === "completed" && prev.status !== "completed") {
          this.trigger("auction_completed", { room_id: data.room_id });
        }
      })
      .catch((e) => console.warn("State polling error:", e));
  }
}

window.auctionSocket = new AuctionSocket();
