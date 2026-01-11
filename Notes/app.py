from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import re
import markdown
import os
import json
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import tempfile

app = Flask(__name__, static_folder='.')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'md', 'txt', 'markdown'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure Local AI Summarization
def initialize_summarizer():
    """Initialize the local summarization system"""
    try:
        print("✅ Local AI summarizer initialized successfully (Rule-based algorithm)")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize summarizer: {e}")
        return False

def summarize_text(text, max_sentences=3):
    """Simple rule-based summarization algorithm"""
    # Split text into sentences using basic punctuation
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) <= max_sentences:
        return text

    # Simple scoring based on sentence position and length
    scored_sentences = []
    for i, sentence in enumerate(sentences):
        # Score based on position (first and last sentences often important)
        position_score = 1.0
        if i == 0 or i == len(sentences) - 1:
            position_score = 2.0

        # Score based on length (medium-length sentences often better)
        word_count = len(sentence.split())
        length_score = 1.0
        if 5 <= word_count <= 20:
            length_score = 1.5

        # Score based on keywords (simple heuristic)
        keywords = ['important', 'key', 'main', 'summary', 'conclusion', 'therefore', 'however']
        keyword_score = 1.0
        sentence_lower = sentence.lower()
        for keyword in keywords:
            if keyword in sentence_lower:
                keyword_score += 0.5

        total_score = position_score * length_score * keyword_score
        scored_sentences.append((total_score, sentence))

    # Sort by score and get top sentences
    scored_sentences.sort(reverse=True, key=lambda x: x[0])
    top_sentences = scored_sentences[:max_sentences]

    # Sort back by original order for coherence
    top_sentences.sort(key=lambda x: sentences.index(x[1]))

    # Create summary
    summary = '. '.join([sentence for _, sentence in top_sentences])
    if not summary.endswith('.'):
        summary += '.'

    return summary

# Initialize the summarizer
summarizer = initialize_summarizer()

# In-memory storage for notes (in production, use a database)
notes_storage = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return send_from_directory('.', 'Notes.html')

@app.route('/demo')
def demo():
    return send_from_directory('.', 'demo.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'features': ['summarize', 'save_notes', 'load_notes', 'list_notes']
    })

@app.route('/api/summarize', methods=['POST'])
def summarize_notes():
    try:
        data = request.get_json()
        notes = data.get('notes', '').strip()

        if not notes:
            return jsonify({'error': 'No notes provided'}), 400

        if not summarizer:
            return jsonify({'error': 'AI summarizer not available. Please check initialization.'}), 500

        # Check if notes are too short
        word_count = len(notes.split())
        if word_count < 10:
            return jsonify({
                'error': 'Notes are too short for summarization. Please provide at least 10 words.',
                'word_count': word_count
            }), 400

        # Generate summary using local algorithm
        summary = summarize_text(notes, max_sentences=3)

        # Clean up the summary
        summary = re.sub(r'\s+', ' ', summary).strip()

        # Generate a unique ID for this summary
        summary_id = str(uuid.uuid4())

        return jsonify({
            'summary': summary,
            'summary_id': summary_id,
            'timestamp': datetime.now().isoformat(),
            'word_count': word_count,
            'summary_word_count': len(summary.split()),
            'model': 'Local Rule-Based Algorithm'
        })

    except Exception as e:
        error_msg = str(e)
        return jsonify({'error': f'Local AI summarization error: {error_msg}'}), 500

@app.route('/api/notes', methods=['POST'])
def save_notes():
    try:
        data = request.get_json()
        notes = data.get('notes', '').strip()
        title = data.get('title', f'Untitled Notes - {datetime.now().strftime("%Y-%m-%d %H:%M")}')

        if not notes:
            return jsonify({'error': 'No notes content provided'}), 400

        # Generate unique ID
        note_id = str(uuid.uuid4())

        note_data = {
            'id': note_id,
            'title': title,
            'content': notes,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'word_count': len(notes.split())
        }

        # Store in memory (in production, save to database)
        notes_storage[note_id] = note_data

        return jsonify({
            'success': True,
            'note_id': note_id,
            'message': 'Notes saved successfully',
            'note': note_data
        })

    except Exception as e:
        return jsonify({'error': f'Failed to save notes: {str(e)}'}), 500

@app.route('/api/notes', methods=['GET'])
def list_notes():
    try:
        # Return list of all notes (in production, add pagination and user filtering)
        notes_list = []
        for note_id, note in notes_storage.items():
            notes_list.append({
                'id': note_id,
                'title': note['title'],
                'created_at': note['created_at'],
                'updated_at': note['updated_at'],
                'word_count': note['word_count']
            })

        # Sort by creation date (newest first)
        notes_list.sort(key=lambda x: x['created_at'], reverse=True)

        return jsonify({
            'notes': notes_list,
            'total_count': len(notes_list)
        })

    except Exception as e:
        return jsonify({'error': f'Failed to list notes: {str(e)}'}), 500

@app.route('/api/notes/<note_id>', methods=['GET'])
def get_note(note_id):
    try:
        if note_id not in notes_storage:
            return jsonify({'error': 'Note not found'}), 404

        return jsonify(notes_storage[note_id])

    except Exception as e:
        return jsonify({'error': f'Failed to retrieve note: {str(e)}'}), 500

@app.route('/api/notes/<note_id>', methods=['PUT'])
def update_note(note_id):
    try:
        if note_id not in notes_storage:
            return jsonify({'error': 'Note not found'}), 404

        data = request.get_json()
        notes = data.get('notes', '').strip()
        title = data.get('title', notes_storage[note_id]['title'])

        if not notes:
            return jsonify({'error': 'No notes content provided'}), 400

        # Update the note
        notes_storage[note_id].update({
            'title': title,
            'content': notes,
            'updated_at': datetime.now().isoformat(),
            'word_count': len(notes.split())
        })

        return jsonify({
            'success': True,
            'message': 'Note updated successfully',
            'note': notes_storage[note_id]
        })

    except Exception as e:
        return jsonify({'error': f'Failed to update note: {str(e)}'}), 500

@app.route('/api/notes/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    try:
        if note_id not in notes_storage:
            return jsonify({'error': 'Note not found'}), 404

        del notes_storage[note_id]

        return jsonify({
            'success': True,
            'message': 'Note deleted successfully'
        })

    except Exception as e:
        return jsonify({'error': f'Failed to delete note: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Clean up the uploaded file
            os.remove(file_path)

            return jsonify({
                'success': True,
                'content': content,
                'filename': filename,
                'word_count': len(content.split())
            })

        return jsonify({'error': 'File type not allowed'}), 400

    except Exception as e:
        return jsonify({'error': f'Failed to upload file: {str(e)}'}), 500

@app.route('/api/export/<note_id>', methods=['GET'])
def export_note(note_id):
    try:
        if note_id not in notes_storage:
            return jsonify({'error': 'Note not found'}), 404

        note = notes_storage[note_id]

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(f"# {note['title']}\n\n")
            f.write(f"Created: {note['created_at']}\n")
            f.write(f"Updated: {note['updated_at']}\n\n")
            f.write("---\n\n")
            f.write(note['content'])
            temp_path = f.name

        return send_file(
            temp_path,
            as_attachment=True,
            download_name=f"{note['title'].replace(' ', '_')}.md",
            mimetype='text/markdown'
        )

    except Exception as e:
        return jsonify({'error': f'Failed to export note: {str(e)}'}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        total_notes = len(notes_storage)
        total_words = sum(note['word_count'] for note in notes_storage.values())

        return jsonify({
            'total_notes': total_notes,
            'total_words': total_words,
            'average_words_per_note': total_words / total_notes if total_notes > 0 else 0,
            'server_uptime': 'N/A',  # Would need to track this in production
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🚀 Starting AI-Driven Markdown Notes Web Server...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("🔑 Make sure OPENAI_API_KEY is set in your environment")
    print("📊 Available endpoints:")
    print("   GET  /api/health - Health check")
    print("   POST /api/summarize - AI summarization")
    print("   GET  /api/notes - List all notes")
    print("   POST /api/notes - Save a note")
    print("   GET  /api/notes/<id> - Get a specific note")
    print("   PUT  /api/notes/<id> - Update a note")
    print("   DELETE /api/notes/<id> - Delete a note")
    print("   POST /api/upload - Upload a file")
    print("   GET  /api/export/<id> - Export a note")
    print("   GET  /api/stats - Get statistics")
    app.run(debug=True, port=5000, host='0.0.0.0')