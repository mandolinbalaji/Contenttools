from flask import Flask, send_from_directory, request, jsonify
import json
import os

app = Flask(__name__)
directory_path = r"G:\My Drive\Music_Scans"

@app.route('/')
def index():
    return send_from_directory(directory_path, 'index.html')

@app.route('/metronome')
def metronome():
    return send_from_directory(directory_path, 'metronome.html')

@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory(directory_path, filename)

@app.route('/songs.json')
def serve_songs():
    return send_from_directory(directory_path, 'songs.json')

@app.route('/save-songs', methods=['POST'])
def save_songs():
    data = request.get_json()
    with open(os.path.join(directory_path, 'songs.json'), 'w') as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)