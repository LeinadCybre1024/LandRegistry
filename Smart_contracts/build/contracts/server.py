from flask import Flask, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='.')
CORS(app)  # Enable CORS for all routes

@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory('.', filename)

if __name__ == "__main__":
    app.run(port=8000)

