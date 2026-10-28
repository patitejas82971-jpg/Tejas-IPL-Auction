import time
import threading
from flask import current_app
from app.extensions import db, socketio, utc_now
from app.models.auction import AuctionRoom
from app.services.bidding_service import finalize_current_player
from app.services.auction_service import advance_to_next_player, get_auction_results_summary

_timer_thread = None
_timer_running = False
_cooldown_rooms = {}  # room_id -> cooldown_end_timestamp

def queue_next_player_cooldown(room_id, delay_seconds=3.5):
    """Sets a celebration cooldown before advancing to the next player."""
    global _cooldown_rooms
    _cooldown_rooms[room_id] = time.time() + delay_seconds

def start_timer_service(flask_app):
    """Background service to manage transitions between players upon hammer completion."""
    global _timer_thread, _timer_running
    if _timer_running:
        return
    _timer_running = True

    def run_timer():
        while _timer_running:
            try:
                with flask_app.app_context():
                    active_rooms = AuctionRoom.query.filter_by(status="active").all()
                    now_ts = time.time()
                    
                    for room in active_rooms:
                        room_channel = f"auction_{room.id}"

                        # Check if room is in celebration cooldown after a hammer strike
                        if room.id in _cooldown_rooms:
                            if now_ts < _cooldown_rooms[room.id]:
                                continue
                            else:
                                del _cooldown_rooms[room.id]
                                # Advance to next player
                                next_ap = advance_to_next_player(room.id)
                                if next_ap:
                                    socketio.emit("player_announced", {
                                        "room_id": room.id,
                                        "player": next_ap.player.to_dict(),
                                        "timer_duration": 0,
                                        "bid_deadline": None
                                    }, room=room_channel)
                                else:
                                    # Auction has ended!
                                    summary = get_auction_results_summary(room.id)
                                    socketio.emit("auction_ended", {
                                        "room_id": room.id,
                                        "results": summary
                                    }, room=room_channel)
                                continue

            except Exception as e:
                # Log without crashing the timer loop
                print(f"[TimerService Error]: {e}")
            
            time.sleep(1)

    _timer_thread = threading.Thread(target=run_timer, daemon=True)
    _timer_thread.start()
    print("Auctioneer Hammer & Transition Service started in background thread.")

