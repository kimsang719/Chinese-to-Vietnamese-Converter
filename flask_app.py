import os
import re
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Cấu hình đường dẫn file
HOME = os.path.expanduser("~")
BASE_DIR = os.path.join(HOME, "mysite")
DICTIONARY_FILE = os.path.join(BASE_DIR, "names.txt")
HAN_VIET_FILE = os.path.join(BASE_DIR, "ChinesePhienAmWords.txt")

def load_dictionary(path):
    dic = {}
    if os.path.exists(path):
        try:
            # Dùng utf-8-sig để xử lý BOM ở đầu file
            with open(path, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    # Loại bỏ ký tự BOM (\ufeff) nếu xuất hiện ở đầu/cuối dòng và xóa khoảng trắng
                    line = line.strip().strip('\ufeff')
                    if line and '=' in line:
                        zh, vn = line.split('=', 1)
                        # Xử lý sạch sẽ từng phần một lần nữa
                        dic[zh.strip().strip('\ufeff')] = vn.strip().strip('\ufeff')
        except Exception as e:
            print(f"Lỗi đọc từ điển tại {path}: {e}")
    return dic

def get_han_viet(text, han_viet_dic):
    res = []
    for char in text:
        # Làm sạch ký tự trước khi tra cứu
        clean_char = char.strip('\ufeff')
        res.append(han_viet_dic.get(clean_char, clean_char))
    return " ".join(res)

def dich_thong_minh(text, dic, han_viet_dic):
    # Làm sạch dữ liệu đầu vào
    text = text.strip().strip('\ufeff')
    if not text: return ""

    # 1. Lấy Hán Việt
    han_viet_str = get_han_viet(text, han_viet_dic)

    # 2. Khóa Name bằng thẻ ZZZ
    sorted_keys = sorted(dic.keys(), key=len, reverse=True)
    placeholders = {}
    temp_text = text
    for i, zh_name in enumerate(sorted_keys):
        tag = f"ZZZ{i}ZZZ"
        if zh_name in temp_text:
            temp_text = temp_text.replace(zh_name, tag)
            placeholders[tag] = dic[zh_name]

    # 3. Gửi đến Google API lấy Pinyin và Tiếng Việt
    viet_raw = ""
    pinyin_str = ""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "zh-CN", "tl": "vi", "dt": ["t", "rm"], "q": temp_text}
        res = requests.get(url, params=params, timeout=10).json()

        viet_raw = "".join([x[0] for x in res[0] if x[0]])
        if len(res[0]) > 1:
            pinyin_str = res[0][-1][3] if len(res[0][-1]) > 3 else ""
    except:
        viet_raw = temp_text
        pinyin_str = "N/A"

    # 4. Giải mã thẻ Name (ZZZ)
    for tag, vn_name in placeholders.items():
        num = tag.replace("ZZZ", "")
        pattern = re.compile(rf"ZZZ\s*{num}\s*ZZZ", re.IGNORECASE)
        viet_raw = pattern.sub(vn_name, viet_raw)
        if pinyin_str:
            pinyin_str = pattern.sub(vn_name, pinyin_str)

    # Trả về theo định dạng: Mỗi loại cách bởi ---, mỗi dòng cách bởi \n
    return (
        f"{text}\n---\n"
        f"{pinyin_str}\n---\n"
        f"{han_viet_str}\n---\n"
        f"{viet_raw}"
    )

@app.route("/", methods=["GET", "POST"])
def index():
    result = ""
    user_input = ""
    if request.method == "POST":
        dic = load_dictionary(DICTIONARY_FILE)
        han_viet_dic = load_dictionary(HAN_VIET_FILE)

        if 'file_input' in request.files and request.files['file_input'].filename != '':
            user_input = request.files['file_input'].read().decode('utf-8-sig')
        else:
            user_input = request.form.get("text_input", "")

        if user_input.strip():
            # Tách dòng và làm sạch từng dòng đầu vào
            lines = [line.strip().strip('\ufeff') for line in user_input.split('\n') if line.strip()]
            results = [dich_thong_minh(line, dic, han_viet_dic) for line in lines]

            result = "\n\n" + "═"*30 + "\n\n".join(results)

    return render_template("index.html", result=result, user_input=user_input)
