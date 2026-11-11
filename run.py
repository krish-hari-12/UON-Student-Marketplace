#Application entry point for UON Student Marketplace.

import os
from dotenv import load_dotenv

# Load environment variables before creating the Flask application.
load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=os.getenv("FLASK_DEBUG") == "1",
    )
