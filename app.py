# app.py
from flask import Flask, render_template
from flask_socketio import SocketIO
import sys

from assistant import JarvisAssistant

# Check if the spaCy model is downloaded, exit if not
try:
    import spacy
    spacy.load("en_core_web_sm")
except OSError:
    print("spaCy model 'en_core_web_sm' not found.")
    print("Please run: python -m spacy download en_core_web_sm")
    sys.exit(1)

app = Flask(__name__)
socketio = SocketIO(app)

# Create a single, shared instance of your assistant
jarvis = JarvisAssistant()
print("Jarvis Assistant has been initialized.")

@app.route('/')
def home():
    """Serves the main user interface."""
    return render_template('jarvis_ui.html')

@socketio.on('connect')
def handle_connect():
    """Handles a new client connection."""
    print('Client connected')
    socketio.emit('assistant_response', {
        'message': f"Hello, I am {jarvis.name}. Click the orb to speak.",
        'state': 'IDLE'
    })

@socketio.on('user_command')
def handle_user_command(data):
    """Receives a command from the UI, processes it, and sends back a response."""
    command = data.get('command')
    if not command:
        return

    print(f"Received command from user: {command}")
    
    response, new_state = jarvis.process_command(command)
    
    print(f"Sending response to UI: {response}")
    socketio.emit('assistant_response', {
        'message': response,
        'state': new_state
    })

if __name__ == '__main__':
    print("Starting Flask server on http://127.0.0.1:5000")
    socketio.run(app, debug=True)