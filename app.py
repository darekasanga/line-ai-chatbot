from flask import Flask, request, jsonify
import os
import requests
import json

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

@app.route('/')
def home():
    return "LINE Flex Messaging API is working!"

@app.route('/webhook', methods=['POST'])
def webhook():
    body = request.get_json()
    print(f"Received body: {body}")

    if body and "events" in body:
        for event in body["events"]:
            if event["type"] == "message" and event["message"]["type"] == "text":
                reply_token = event["replyToken"]
                user_message = event["message"]["text"]
                reply_flex_message(reply_token, user_message)
    return "OK"

def reply_flex_message(reply_token, message_text):
    flex_message = {
        "type": "flex",
        "altText": "Upload File",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "Upload a File",
                        "weight": "bold",
                        "size": "xl",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "Select a file to upload:",
                                "size": "sm",
                                "margin": "md"
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "uri",
                                    "label": "Upload",
                                    "uri": "https://line-ai-chatbot.vercel.app/upload.html"
                                },
                                "style": "primary",
                                "color": "#1DB446",
                                "margin": "sm"
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "uri",
                                    "label": "View Uploaded Files",
                                    "uri": "https://line-ai-chatbot.vercel.app/list"
                                },
                                "style": "secondary",
                                "margin": "sm"
                            }
                        ],
                        "margin": "md"
                    }
                ]
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    payload = {
        "replyToken": reply_token,
        "messages": [flex_message]
    }

    response = requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers=headers,
        data=json.dumps(payload)
    )
    print(f"LINE API response: {response.status_code} - {response.text}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
