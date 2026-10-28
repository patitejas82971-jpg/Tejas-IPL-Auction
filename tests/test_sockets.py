import pytest
from app import create_app
from app.extensions import db, socketio
from app.models.user import User
from app.models.auction import AuctionRoom
from app.services.auction_service import create_auction_room, select_franchise, start_auction_service

@pytest.fixture(scope="module")
def socket_app():
    return create_app("testing")

@pytest.fixture
def socket_setup(socket_app):
    app = socket_app
    with app.app_context():
        db.create_all()
        u = User(username="socket_tester", email="tester@ipl.com")
        u.set_password("pass123")
        db.session.add(u)
        db.session.commit()

        room = create_auction_room(user_id=u.id, room_name="Socket Arena")
        select_franchise(room.id, u.id, "CSK")
        start_auction_service(room.id, u.id)

        yield app, room, u
        db.session.remove()
        db.drop_all()

def test_socket_join_room_and_state(socket_setup):
    app, room, user = socket_setup
    client = socketio.test_client(app, flask_test_client=app.test_client())
    
    assert client.is_connected()
    client.emit("join_room", {"room_id": room.id, "username": user.username})
    
    received = client.get_received()
    event_names = [e["name"] for e in received]
    assert "user_joined" in event_names
    assert "auction_state" in event_names
    client.disconnect()

def test_socket_request_auction_state(socket_setup):
    app, room, user = socket_setup
    client = socketio.test_client(app, flask_test_client=app.test_client())
    assert client.is_connected()
    client.get_received()  # flush any connect events
    client.emit("request_auction_state", {"room_id": room.id})
    received = client.get_received()
    event_names = [e["name"] for e in received]
    assert "auction_state" in event_names
    client.disconnect()
