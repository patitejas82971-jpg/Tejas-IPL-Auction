import os
import sys

# Add project root to sys.path so app modules are discoverable
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.environ.setdefault("VERCEL", "1")

from run import app

# Vercel serverless function entrypoint
# Exposes both 'app' and 'handler' callable for WSGI runtime compatibility
handler = app
