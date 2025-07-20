@app.post("/callback")
async def callback(request: Request):
    try:
        body = await request.json()
        print("LINE受信内容:", body)

        
        return "ok"
    except Exception as e:
        import traceback
        traceback.print_exc()  # ← ✅ これが重要です！
        return {"error": str(e)}

        
        events = body.get("events", [])
        for event in events:
            if event["type"] == "message" and event["message"]["type"] == "image":
                reply_token = event["replyToken"]
                message_id = event["message"]["id"]

                image_res = requests.get(
                    f"https://api-data.line.me/v2/bot/message/{message_id}/content",
                    headers={"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
                )
                image_bytes = image_res.content

                # オリジナル画像を保存
                original_filename = f"{message_id}.jpg"
                original_url = save_image_to_github(image_bytes, original_filename)

                # リサイズ画像を保存
                resized_data = resize_image(image_bytes)
                resized_filename = f"{message_id}_resized.jpg"
                resized_url = save_image_to_github(resized_data, resized_filename)

                # FlexMessage送信
                send_flex_message(
                    reply_token,
                    preview_url=resized_url,
                    original_url=original_url,
                    resized_url=resized_url
                )
        return "ok"
    except Exception as e:
        import traceback
        traceback.print_exc()  # ← 詳しいエラーを出力
        return {"error": str(e)}
