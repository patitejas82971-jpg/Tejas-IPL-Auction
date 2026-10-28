import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "ipl-super-secret-dev-key-change-in-production")
    
    database_url = os.getenv("DATABASE_URL")
    if os.getenv("VERCEL"):
        # On Vercel, the lambda filesystem is strictly read-only except for /tmp
        if not database_url or database_url.startswith("sqlite"):
            database_url = "sqlite:////tmp/ipl_auction.db"
        elif database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
    else:
        if not database_url:
            database_url = f"sqlite:///{os.path.join(BASE_DIR, 'ipl_auction.db')}"
        elif database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Gemini AI configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # Cricket Data API (optional)
    CRICKET_API_KEY = os.getenv("CRICKET_API_KEY", "")
    
    # SocketIO configuration
    SOCKETIO_PING_TIMEOUT = 30
    SOCKETIO_PING_INTERVAL = 10
    
    # Security & session
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


from sqlalchemy.pool import StaticPool

class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool
    }
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
