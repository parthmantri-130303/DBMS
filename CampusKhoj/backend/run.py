from backend.app import create_app
from backend.config import config

app = create_app()

if __name__ == "__main__":
    print(f"Starting CampusKhoj API on http://127.0.0.1:{config.PORT}")
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)

