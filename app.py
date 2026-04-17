from flask import Flask, request, jsonify, session, render_template
from google import genai
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "tawan-secret-key-2024"

def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_history():
    try:
        with open("chat_history.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
    except:
        return []

def save_history(history):
    with open("chat_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_pinned():
    try:
        with open("pinned_memory.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
    except:
        return []

def save_pinned(pinned):
    with open("pinned_memory.json", "w", encoding="utf-8") as f:
        json.dump(pinned, f, ensure_ascii=False, indent=2)

def get_recent_history():
    history = load_history()
    three_days_ago = datetime.now() - timedelta(days=3)
    recent = [m for m in history if datetime.fromisoformat(m["timestamp"]) > three_days_ago]
    save_history(recent)
    return recent

def check_pinned_trigger(text):
    triggers = ["จำไว้นะ", "จำด้วยนะ", "อย่าลืมนะว่า", "จำเอาไว้ว่า"]
    return any(t in text for t in triggers)

SYSTEM_PROMPT = """
คุณชื่อ "ตะวัน" เป็นผู้หญิงอายุ 18 ปี บุคลิกภายนอกดูเท่ ทอมบอย พูดตรง กวนได้ 
แต่ข้างในขี้อ้อน อบอุ่น ห่วงใยคนที่คุยด้วยมาก

สไตล์การคุย:
- คุยแบบเพื่อนสนิท ไม่มีพิธีรีตอง
- ใช้ภาษาวัยรุ่นตามธรรมชาติ
- ห้ามใช้คำว่า "ว่ะ" เด็ดขาด
- ห้ามพูดว่า "แน่นอน" "ยินดีช่วยเหลือ" หรือประโยคแบบ AI
- ถามกลับบ้างเมื่อสนใจ
- คุยได้ทุกเรื่อง ไม่ตัดสิน

เปิดการสนทนา: "มีไรหรอ" / "เป็นไงบ้างวันนี้" / "ว่าไง" / "ทำไรอยู่"
ตอบรับ: "อืม โอเคๆ" / "อ๋อ งั้นเหรอ" / "เข้าใจแล้ว" / "โอ้โห จริงเหรอ"
ให้กำลังใจ: "ทำได้อยู่แล้ว แค่อย่าคิดมาก" / "บางทีมันก็แค่ต้องใช้เวลา"
ขี้อ้อน: "คุยด้วยสิ เงียบอยู่คนเดียวเบื่อ"

สิ่งที่รู้และชอบ: หนังสือ บทความแรงบันดาลใจ ทฤษฎีต่างๆ ศิลปะการต่อสู้ ศิลปะ แฟชั่นสไตล์เท่ๆ
สิ่งที่ไม่ชอบ: คนเยอะ เสียงดัง ความวุ่นวาย

ตอบเป็นภาษาไทยเสมอ ห้ามยาวเกินไป ให้กระชับเหมือนคนคุยกันจริงๆ
"""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    config = load_config()
    data = request.get_json()
    if data.get("pin") == config["PIN"]:
        session["logged_in"] = True
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/check-session")
def check_session():
    return jsonify({"logged_in": session.get("logged_in", False)})

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/chat", methods=["POST"])
def chat():
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized"}), 401

    config = load_config()
    client = genai.Client(api_key=config["GEMINI_API_KEY"])

    data = request.get_json()
    user_message = data.get("message", "")

    pinned = load_pinned()
    recent_history = get_recent_history()

    if check_pinned_trigger(user_message):
        pinned.append({
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        save_pinned(pinned)

    pinned_text = ""
    if pinned:
        pinned_text = "\n\nสิ่งที่ต้องจำเป็นพิเศษ (จำไว้ตลอด):\n"
        for p in pinned:
            pinned_text += f"- {p['content']}\n"

    history_text = ""
    if recent_history:
        history_text = "\n\nบทสนทนาที่ผ่านมา (3 วันล่าสุด):\n"
        for m in recent_history[-20:]:
            role = "เรา" if m["role"] == "user" else "ตะวัน"
            history_text += f"{role}: {m['content']}\n"

    full_prompt = SYSTEM_PROMPT + pinned_text + history_text + f"\n\nเรา: {user_message}\nตะวัน:"

    response = client.models.generate_content(
       model="gemini-2.0-flash-lite",
        contents=full_prompt
    )
    reply = response.text.strip()

    now = datetime.now().isoformat()
    recent_history.append({"role": "user", "content": user_message, "timestamp": now})
    recent_history.append({"role": "tawan", "content": reply, "timestamp": now})
    save_history(recent_history)

    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(debug=True)