import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

app = Flask(__name__)

# 從環境變數讀取金鑰 (部署時在平台上設定)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 設定 Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash')

def get_ai_response(user_input, mode="auto"):
    try:
        if mode == "translate":
            prompt = f"請將這段文字翻譯成地道的英文，並提供兩種語氣風格（正式與非正式）：'{user_input}'"
        else:
            prompt = f"你是一個英文家教。使用者說：'{user_input}'。如果是英文，請翻譯成中文並給出優化建議；如果是中文，請翻譯成英文。"
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"AI 發生錯誤: {e}")
        return "抱歉，我的 AI 大腦暫時斷線了，請稍後再試！"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    
    # 邏輯判斷
    if msg.lower().startswith('/t '):
        # 強制翻譯模式
        target_text = msg[3:]
        reply = get_ai_response(target_text, mode="translate")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        
    elif any(char.isalpha() for char in msg) and len(msg.split()) >= 2:
        # 自動偵測模式：包含英文字母且長度超過 2 個單字
        reply = get_ai_response(msg, mode="auto")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    # 部署平台會自動分配 PORT
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)