import pytest
from app import create_app
from app.extensions import db
from app.models.user import User

@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def test_user_password_hashing():
    u = User(username="captain_cool", email="dhoni@csk.com")
    u.set_password("finisher7")
    assert u.password_hash != "finisher7"
    assert u.check_password("finisher7") is True
    assert u.check_password("wrong_pass") is False

def test_user_registration(client):
    res = client.post("/api/auth/register", json={
        "username": "rohit45",
        "email": "rohit@mumbai.com",
        "password": "hitmanpassword"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["username"] == "rohit45"

def test_duplicate_user_registration(client):
    client.post("/api/auth/register", json={
        "username": "virat18",
        "email": "virat@rcb.com",
        "password": "kingpassword"
    })
    res2 = client.post("/api/auth/register", json={
        "username": "virat18",
        "email": "another@rcb.com",
        "password": "kingpassword"
    })
    assert res2.status_code == 409
    data = res2.get_json()
    assert data["success"] is False

def test_user_login(client):
    client.post("/api/auth/register", json={
        "username": "jaddu8",
        "email": "jaddu@csk.com",
        "password": "swordcelebration"
    })
    # Valid login
    res = client.post("/api/auth/login", json={
        "username_or_email": "jaddu8",
        "password": "swordcelebration"
    })
    assert res.status_code == 200
    assert res.get_json()["success"] is True

    # Invalid login
    res_bad = client.post("/api/auth/login", json={
        "username_or_email": "jaddu8",
        "password": "wrong_password"
    })
    assert res_bad.status_code == 401
    assert res_bad.get_json()["success"] is False
