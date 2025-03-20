from flask import Flask, request, jsonify, render_template
import os
import json
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp/uploads"  # Temporary folder for uploaded files
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Logging function for chatbot conversations
def log_conversation(user_message, bot_response, message_type):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message_type": message_type,
        "user": user_message,
        "bot": bot_response
    }
    print("Logging conversation:", json.dumps(log_entry, ensure_ascii=False, indent=4))

# Chatbot webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print("Received data:", data)

        if not data or 'events' not in data or len(data['events']) == 0:
            print("No events found in data!")
            return jsonify({"status": "no events", "message": "No message events received"}), 200

        for event in data['events']:
            message_type = event.get('message', {}).get('type', 'unknown')
            user_message = event.get('message', {}).get('text', 'Unknown message')
            print(f"Message Type: {message_type} - User Message: {user_message}")

            # Simple response logic
            if "hello" in user_message.lower():
                bot_response = "Hello! How can I assist you today?"
            elif "help" in user_message.lower():
                bot_response = "Sure! Let me know how I can help you."
            elif "thanks" in user_message.lower():
                bot_response = "You're welcome!"
            else:
                bot_response = "I'm sorry, I didn't understand that. Please try asking in a different way."

            # Log the conversation
            log_conversation(user_message, bot_response, message_type)
            print("Bot response:", bot_response)

        response = {
            "status": "success",
            "message": "Webhook received",
            "data": data
        }
        return jsonify(response), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# File upload endpoint
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400

    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        return jsonify({"status": "success", "message": f"File uploaded to {file_path}"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# File upload page
@app.route('/upload.html')
def upload_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Uploader</title>
    </head>
    <body>
        <h2>Upload a File</h2>
        <form id="uploadForm" enctype="multipart/form-data" method="POST" action="/upload">
            <input type="file" name="file" required>
            <button type="submit">Upload</button>
        </form>
    </body>
    </html>
    '''

# Home page
@app.route('/')
def home():
    return "Hello, LINE AI Chatbot and File Uploader are running!", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
