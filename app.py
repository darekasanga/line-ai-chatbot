from flask import Flask, request, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)

LOG_FILE = "chat_logs.json"

def log_conversation(user_message, bot_response):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_message,
        "bot": bot_response
    }
    
    # Load existing logs
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    else:
        logs = []

    # Append new log and save
    logs.append(log_entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=4)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print("Received data:", data)

        if not data or 'events' not in data or len(data['events']) == 0:
            print("No events found in data!")
            return jsonify({"status": "no events", "message": "No message events received"}), 200

        for event in data['events']:
            user_message = event.get('message', {}).get('text', 'Unknown message')
            print("User message:", user_message)
            
            # Simple response logic
            if user_message.lower() == "hello":
                bot_response = "Hello, how can I assist you today?"
            else:
                bot_response = "Sorry, I am not trained to answer that question."
            
            # Log the conversation
            log_conversation(user_message, bot_response)
            
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

@app.route('/')
def home():
    return "Hello, LINE AI Chatbot is running!", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
