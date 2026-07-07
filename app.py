# app.py
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import sys
import os
from werkzeug.utils import secure_filename

from assistant import JarvisAssistant
from session_context import get_session_context, delete_session_context
from rag.chunking import split_text
from rag.embeddings import get_embeddings
from rag.vector_store import SessionVectorStore
from pypdf import PdfReader
import docx

# Check if the spaCy model is downloaded, exit if not
try:
    import spacy
    spacy.load("en_core_web_sm")
except OSError:
    print("spaCy model 'en_core_web_sm' not found.")
    print("Please run: python -m spacy download en_core_web_sm")
    sys.exit(1)

app = Flask(__name__)
# Explicitly use threading async mode for concurrent Socket.IO handler execution
socketio = SocketIO(app, async_mode="threading")

# Create a single, shared instance of your assistant
jarvis = JarvisAssistant()
print("Jarvis Assistant has been initialized.")

@app.route('/')
def home():
    """Serves the main user interface."""
    return render_template('jarvis_ui.html')

@socketio.on('connect')
def handle_connect():
    """Handles a new client connection with an onboarding message."""
    print(f'Client connected: {request.sid}')
    # Initialize session context
    get_session_context(request.sid)
    # --- ONBOARDING MESSAGE ---
    welcome_message = f"Hello, I am {jarvis.name}. You can ask me for the weather, news, or say 'help' to see all commands."
    socketio.emit('assistant_response', {
        'message': welcome_message,
        'state': 'IDLE',
        'source': 'skill',
        'confidence': 1.0
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handles client disconnection by cleaning up context."""
    print(f'Client disconnected: {request.sid}')
    delete_session_context(request.sid)

@socketio.on('user_command')
def handle_user_command(data):
    """Receives a command from the UI, processes it, and sends back a response."""
    command = data.get('command')
    if not command:
        return

    print(f"Received command from user: {command}")
    
    response, new_state = jarvis.process_command(command)
    ctx = get_session_context(request.sid)
    source = ctx.get('last_source', 'skill')
    confidence = ctx.get('last_confidence', 1.0)
    
    print(f"Sending response to UI: {response} (source: {source}, conf: {confidence})")
    socketio.emit('assistant_response', {
        'message': response,
        'state': new_state,
        'source': source,
        'confidence': confidence
    })

# --- FILE UPLOAD & INDEXING ENDPOINT ---
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path):
    ext = file_path.rsplit('.', 1)[1].lower()
    if ext == 'txt':
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext == 'pdf':
        reader = PdfReader(file_path)
        text_list = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_list.append(t)
        return "\n".join(text_list)
    elif ext == 'docx':
        doc_obj = docx.Document(file_path)
        return "\n".join([p.text for p in doc_obj.paragraphs])
    return ""

def rebuild_session_index(session_id):
    session_docs_dir = os.path.join("documents", session_id)
    index_path = os.path.join("documents", f"index_{session_id}.faiss")
    map_path = os.path.join("documents", f"map_{session_id}.json")
    
    # Delete index files first so SessionVectorStore initializes empty
    if os.path.exists(index_path):
        try:
            os.remove(index_path)
        except Exception:
            pass
    if os.path.exists(map_path):
        try:
            os.remove(map_path)
        except Exception:
            pass
            
    if not os.path.exists(session_docs_dir):
        return
        
    remaining_files = [f for f in os.listdir(session_docs_dir) if allowed_file(f)]
    
    if not remaining_files:
        # If directory is empty, remove it
        try:
            os.rmdir(session_docs_dir)
        except Exception:
            pass
        return
        
    store = SessionVectorStore(session_id)
    all_chunks = []
    
    for filename in remaining_files:
        file_path = os.path.join(session_docs_dir, filename)
        try:
            text = extract_text_from_file(file_path)
            if text.strip():
                chunks = split_text(text)
                all_chunks.extend(chunks)
        except Exception as e:
            print(f"Error reading {filename} during index rebuild: {e}")
            
    if all_chunks:
        embeddings = get_embeddings(all_chunks)
        store.add_chunks(all_chunks, embeddings)

@app.route('/upload', methods=['POST'])
def upload_file():
    session_id = request.form.get('session_id')
    if not session_id:
        return jsonify({'error': 'No session ID provided'}), 400
        
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        session_docs_dir = os.path.join("documents", session_id)
        os.makedirs(session_docs_dir, exist_ok=True)
        file_path = os.path.join(session_docs_dir, filename)
        file.save(file_path)
        
        try:
            text = extract_text_from_file(file_path)
        except Exception as e:
            return jsonify({'error': f'Failed to parse file: {str(e)}'}), 500
            
        if not text.strip():
            return jsonify({'error': 'No text could be extracted from the file'}), 400
            
        # Chunk text, embed, and index
        chunks = split_text(text)
        embeddings = get_embeddings(chunks)
        
        store = SessionVectorStore(session_id)
        store.add_chunks(chunks, embeddings)
        
        return jsonify({
            'message': f'File {filename} successfully indexed',
            'chunks': len(chunks)
        })
    else:
        return jsonify({'error': 'Invalid file type'}), 400

@app.route('/documents', methods=['GET'])
def list_documents():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'No session ID provided'}), 400
        
    session_docs_dir = os.path.join("documents", session_id)
    if not os.path.exists(session_docs_dir):
        return jsonify({'documents': []})
        
    docs = []
    for filename in os.listdir(session_docs_dir):
        if allowed_file(filename):
            file_path = os.path.join(session_docs_dir, filename)
            try:
                size = os.path.getsize(file_path)
                docs.append({'name': filename, 'size': size})
            except Exception:
                pass
    return jsonify({'documents': docs})

@app.route('/documents', methods=['DELETE'])
def delete_document():
    session_id = request.args.get('session_id') or (request.json.get('session_id') if request.is_json else None)
    filename = request.args.get('filename') or (request.json.get('filename') if request.is_json else None)
    
    if not session_id:
        return jsonify({'error': 'No session ID provided'}), 400
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400
        
    filename = secure_filename(filename)
    file_path = os.path.join("documents", session_id, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': f'Document {filename} not found'}), 404
        
    try:
        os.remove(file_path)
        rebuild_session_index(session_id)
        return jsonify({'message': f'Document {filename} deleted and index rebuilt successfully'})
    except Exception as e:
        return jsonify({'error': f'Failed to delete document: {str(e)}'}), 500

if __name__ == '__main__':
    print("Starting Flask server on http://127.0.0.1:5000")
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)