
import sys
import os
import eventlet
eventlet.monkey_patch()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from app import create_app, socketio

from dotenv import load_dotenv

load_dotenv()


app, socketio = create_app()

if __name__ == "__main__":
    print("✅ Flask app running at http://localhost:5000")
    socketio.run(app, debug=True)
