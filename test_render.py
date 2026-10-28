from app import create_app
from app.models.user import User

app = create_app()
client = app.test_client()

with app.app_context():
    u = User.query.get(1)
    with client.session_transaction() as sess:
        sess['_user_id'] = str(u.id)
        sess['_fresh'] = True
    
    res = client.get('/auction/6')
    html = res.data.decode('utf-8')
    idx = html.find('id="poolsModal"')
    idx2 = html.find('auction.js')
    print("--- SNIPPET END OF poolsModal ---")
    print(html[idx2-500:idx2+200])
