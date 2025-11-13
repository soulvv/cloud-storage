from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from flask import render_template
import os
import json
from io import BytesIO  # Added for file streaming

app = Flask(__name__)

# Configuration
BASE_DIR = os.path.abspath("uploads")  # Directory for file storage
USER_FILE = os.path.abspath("users.json")  # User database file

# Ensure directories and files exist
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        json.dump({}, f)

# Helper Functions
def load_users():
    with open(USER_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

# Routes
@app.route('/')
def home():
    """Home route."""
    return render_template('home.html')

@app.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    users = load_users()
    username = request.form['username']
    password = request.form['password']

    if username in users:
        return jsonify({"error": "User already exists"}), 400

    key = Fernet.generate_key()  # Generate encryption key for this user
    users[username] = {"password": password, "key": key.decode("utf-8")}

    user_dir = os.path.join(BASE_DIR, username)
    os.makedirs(user_dir)

    save_users(users)
    return jsonify({"message": f"User {username} registered successfully."}), 200


@app.route('/upload', methods=['POST'])
def upload_file():
    """Upload and encrypt a file."""
    users = load_users()
    username = request.form['username']
    password = request.form['password']

    if username not in users or users[username]['password'] != password:
        return jsonify({"error": "Authentication failed"}), 401

    file = request.files['file']
    if not file:
        return jsonify({"error": "No file provided"}), 400

    filename = secure_filename(file.filename)
    user_dir = os.path.join(BASE_DIR, username)
    file_path = os.path.join(user_dir, filename)

    fernet = Fernet(users[username]['key'])
    encrypted_data = fernet.encrypt(file.read())

    with open(file_path, "wb") as f:
        f.write(encrypted_data)

    return jsonify({"message": f"File {filename} uploaded successfully."}), 200


@app.route('/files', methods=['POST'])
def list_files():
    """List the files for a specific user."""
    users = load_users()
    username = request.form['username']
    password = request.form['password']

    if username not in users or users[username]['password'] != password:
        return jsonify({"error": "Authentication failed"}), 401

    user_dir = os.path.join(BASE_DIR, username)
    files = os.listdir(user_dir)

    return jsonify({"files": files}), 200


@app.route('/download', methods=['POST'])
def download_file():
    """Download and decrypt a file."""
    users = load_users()
    username = request.form['username']
    password = request.form['password']
    filename = request.form['filename']

    if username not in users or users[username]['password'] != password:
        return jsonify({"error": "Authentication failed"}), 401

    user_dir = os.path.join(BASE_DIR, username)
    file_path = os.path.join(user_dir, filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # Decrypt file
    fernet = Fernet(users[username]['key'])
    with open(file_path, "rb") as f:
        encrypted_data = f.read()

    decrypted_data = fernet.decrypt(encrypted_data)

    # Serve the decrypted file directly
    return send_file(
        BytesIO(decrypted_data),
        mimetype="application/octet-stream",
        download_name=filename,
        as_attachment=True
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
 