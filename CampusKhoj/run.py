import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app import create_app
from backend.config import config

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", config.PORT))
    print(f"Starting CampusKhoj API on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)

