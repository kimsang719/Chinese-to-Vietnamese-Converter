import os
import re
from flask import Flask, render_template, request

app = Flask(__name__)

# --- CẤU HÌNH ĐƯỜNG DẪN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIETPHRASE_FILE = os.path.join(BASE_DIR, "VietPhrase.txt")
HAN_VIET_FILE = os.path.join(BASE_DIR, "ChinesePhienAmWords.txt")

def load_dictionary(path):
    dic = {}
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line:
                        zh, vn = line.split('=', 1)
                        # VietPhrase thường có dạng: Trung Quốc=中国 (hoặc ngược lại)
                        # Tùy file của bạn, ở đây mặc định Trung=Việt
                        dic[zh.strip()] = vn.strip()
        except Exception as e:
            print(f"Lỗi đọc từ điển tại {path}: {e}")
    return dic

# Nạp từ điển vào bộ nhớ
VP_DIC = load_dictionary(VIETPHRASE_FILE)
HV_DIC = load_dictionary(HAN_VIET_FILE)
# Sắp xếp key theo độ dài giảm dần để ưu tiên dịch cụm từ dài trước
SORTED_VP_KEYS = sorted(VP_DIC.keys(), key=len, reverse=True)

def translate_vietphrase(text):
    """
    Dịch văn bản bằng thuật toán duyệt cụm từ dài nhất (Longest Match).
    """
    i = 0
    result = []
    n = len(text)
    
    while i < n:
        match = None
        # Kiểm tra xem có cụm từ nào khớp trong VietPhrase không
        for key in SORTED_VP_KEYS:
            if text.startswith(key, i):
                match = key
                break
        
        if match:
            # Nếu thấy trong VietPhrase, lấy nghĩa tương ứng
            result.append(VP_DIC[match])
            i += len(match)
        else:
            # Nếu không thấy, lấy 1 ký tự và tra âm Hán Việt
            char = text[i]
            result.append(HV_DIC.get(char, char))
            i += 1
            
    return " ".join(result)

def get_han_viet(text):
    res = [HV_DIC.get(char, char) for char in text]
    return " ".join(res)

def process_translation(text):
    text = text.strip()
    if not text: return ""

    han_viet_str = get_han_viet(text)
    viet_phrase_str = translate_vietphrase(text)

    # Vì không dùng API nên pinyin ở đây có thể để trống hoặc 
    # nếu bạn có file Pinyin riêng thì nạp tương tự Hán Việt.
    return (
        f"Gốc: {text}\n"
        f"Hán Việt: {han_viet_str}\n"
        f"VietPhrase: {viet_phrase_str}"
    )

@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    user_input = ""
    if request.method == "POST":
        if 'file_input' in request.files and request.files['file_input'].filename != '':
            user_input = request.files['file_input'].read().decode('utf-8-sig')
        else:
            user_input = request.form.get("text_input", "")

        if user_input.strip():
            lines = [line.strip() for line in user_input.split('\n') if line.strip()]
            results = [process_translation(line) for line in lines]
            result = "\n\n" + "═"*30 + "\n\n".join(results)

    return render_template("index.html", result=result, user_input=user_input)

@app.route("/cron-task")
def cron_task():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

