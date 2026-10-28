# 🏏 IPL Auction Simulator

A full-featured, real-time **IPL Auction Simulator** web application built with **Flask**, **Flask-SocketIO**, **SQLAlchemy**, and **Google Gemini AI**. Experience the thrill of the Indian Premier League mega-auction with live bidding, authoritative countdown timers, interactive squad management, and AI-powered bidding intelligence. Friends can create teams, bid on players, manage budgets, and compete in IPL-style auctions.

---

## 🌟 Key Features

- **⚡ Real-Time Live Bidding**: WebSocket-powered live auction room with instant bid updates and authoritative server-side countdown timers.
- **🤖 Gemini AI Assistant**: AI-driven bidding recommendations, player valuation insights, and team composition analysis powered by Google Gemini.
- **🏏 Authentic IPL Experience**: Official 10 IPL franchises, player categories (Batsmen, Bowlers, All-rounders, Wicketkeepers), overseas limits, and salary purse tracking (₹100 Cr+).
- **📊 Team Dashboard & Roster**: Track your squad's purse balance, overseas player counts, role breakdowns, and bench strength in real-time.
- **🔒 Authentication**: Secure user registration, login, and session management with Flask-Login.
- **📱 Android Mobile App**: Complete Android client with Material 3 dark styling, real-time live bidding, native haptic feedback, offline fallback, and in-app server configuration.
- **🎨 Modern Dark UI**: Sleek, responsive, cricket-themed dark design crafted with custom CSS and dynamic UI elements.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12, Flask, Flask-SocketIO (Simple-WebSocket / Threading)
- **Database**: SQLite (default) / PostgreSQL (production ready via SQLAlchemy)
- **AI Integration**: Google Gemini API (`google-generativeai`)
- **Frontend**: HTML5, Vanilla CSS, JavaScript (Socket.IO client)
- **Testing**: Pytest (16+ automated test suites)

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/patitejas82971-jpg/IPL-Auction-2026.git
cd IPL-Auction-2026
```

### 3. Set Up Virtual Environment (Recommended)
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to provide your configuration:
```ini
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your_secret_key_here
DATABASE_URL=sqlite:///ipl_auction.db
GEMINI_API_KEY=your_google_gemini_api_key
PORT=5000
```

### 6. Run the Application
```bash
python run.py
```
Open your browser and navigate to:
```
http://localhost:5000
```

---

## 🧪 Running Tests

Run the comprehensive test suite with:
```bash
pytest
```

---

## 📁 Project Structure

```text
IPL-Auction/
├── android/             # Android mobile app (Kotlin, Material 3, WebView Bridge)
├── app/
│   ├── models/          # SQLAlchemy database models (User, Team, Player, Bid)
│   ├── routes/          # Flask blueprints (auth, auction, team, player, ai)
│   ├── services/        # Business logic (bidding, timer, AI, player seeding)
│   ├── sockets/         # WebSocket event handlers
│   ├── static/          # CSS stylesheets, JavaScript files, images
│   ├── templates/       # Jinja2 HTML templates
│   ├── config.py        # Environment configuration
│   └── extensions.py    # Flask extension initializations
├── data/                # Initial JSON data (players, teams, rules)
├── instance/            # Local SQLite database (git-ignored)
├── scripts/             # Data generation and seeding scripts
├── tests/               # Pytest test cases
├── .env.example         # Example environment template
├── requirements.txt     # Python package requirements
├── run.py               # Main application entry point
└── README.md            # Project documentation
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
