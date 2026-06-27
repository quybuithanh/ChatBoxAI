"""
TRỢ LÝ HỎI-ĐÁP THEO LUẬT (rule-based assistant) — KHUNG BÀI LÀM (STARTER).

>>> HƯỚNG DẪN:
    1. Đọc kỹ DE_THI.pdf trước.
    2. Hoàn thiện mọi chỗ ghi "TODO" (xoá dòng `raise NotImplementedError`).
    3. KHÔNG đổi tên hàm/lớp/tham số đã cho (bộ test dựa vào đúng các tên này).
    4. Lưu tệp này thành  solution.py  rồi chạy:  python3 test_solution.py
       -> Đạt khi in ra "ALL TESTS PASSED".
    5. Chạy thử trợ lý:  python3 solution.py

Gợi ý chung: phần CLI (PHẦN E) đã viết sẵn cho bạn — chỉ cần hoàn thành
phần lõi A, B, C, D là chương trình chạy được.
"""

import abc
import argparse
import json
import os
import unicodedata
from datetime import datetime
import random

# --------------------------------------------------------------------------- #
# Hằng số cấu hình (giữ nguyên)
# --------------------------------------------------------------------------- #
DEFAULT_THRESHOLD = 0.5
FALLBACK = "Xin lỗi, mình chưa hiểu ý bạn. Bạn thử hỏi cách khác nhé!"
HERE = os.path.dirname(os.path.abspath(__file__))


class KnowledgeBaseError(Exception):
    """Lỗi khi nạp/đọc kho tri thức (tệp thiếu, JSON hỏng, sai định dạng)."""


# --------------------------------------------------------------------------- #
# PHẦN A — Tiện ích xử lý văn bản (Bài 2, 3, 4)
# --------------------------------------------------------------------------- #
def strip_accents(text):
    """Bỏ dấu tiếng Việt và đổi đ/Đ -> d/D. Ví dụ: 'Chào Đại' -> 'Chao Dai'.

    Gợi ý:
      - Đổi 'đ'->'d', 'Đ'->'D' bằng str.replace (vì NFD không tách được đ).
      - unicodedata.normalize('NFD', text) tách chữ và dấu thành 2 ký tự.
      - Bỏ các ký tự có unicodedata.category(ch) == 'Mn' (dấu thanh).
    """
    text = text.replace('đ', 'd').replace('Đ', 'D')

    normalized = unicodedata.normalize('NFD', text)

    result = ''
    for ch in normalized:
        if unicodedata.category(ch) != 'Mn':
            result += ch
    return result


def normalize(text):
    """Chuẩn hoá: bỏ dấu -> chữ thường -> bỏ dấu câu -> gộp khoảng trắng.

    'Wi-Fi của Khoa?!' -> 'wi fi cua khoa'
    Gợi ý: dùng strip_accents, .lower(), ch.isalnum(), và ' '.join(s.split()).
    """
    text = strip_accents(text)

    text = text.lower()

    result = ''
    for ch in text:
        if(ch.isalnum()):
            result += ch
        else:
            result += ' '

    text = ' '.join(result.split())

    return text


def tokenize(text):
    """Tách văn bản đã chuẩn hoá thành danh sách từ. '' -> []."""
    return normalize(text).split()


def keyword_score(text_tokens, pattern_tokens):
    """Tỉ lệ từ-khoá của MẪU xuất hiện trong câu người dùng (0.0 – 1.0).

    score = |giao của hai tập| / |số từ trong mẫu| ; mẫu rỗng -> 0.0.
    Gợi ý: ép cả hai tham số sang set, dùng phép giao &.
    """
    pattern_set = set(pattern_tokens)
    
    if not pattern_set:
        return 0.0

    text_set = set(text_tokens)

    return len(text_set & pattern_set) / len(pattern_set)


# --------------------------------------------------------------------------- #
# PHẦN B — Intent & KnowledgeBase (Bài 5 + Bài 6)
# --------------------------------------------------------------------------- #
class Intent:
    """Một 'ý định' người dùng: gồm tag, các mẫu câu và các câu trả lời."""

    def __init__(self, tag, patterns, responses):
        self._tag = tag
        self._patterns = list(patterns)
        self._responses = list(responses)
        self._last = None

    @property
    def tag(self):
        return self._tag

    @property
    def patterns(self):
        return self._patterns

    @property
    def responses(self):
        return self._responses

    def score(self, user_tokens):
        """Điểm khớp cao nhất giữa câu người dùng (tập từ) và các mẫu của intent.

        Gợi ý: max(keyword_score(user_tokens, tokenize(p)) for p in patterns);
        nếu không có mẫu nào -> 0.0.
        """
        if not self._patterns:
            return 0.0

        return max(
            keyword_score(user_tokens, tokenize(pattern))
            for pattern in self._patterns
        )

    def reply(self, index=None):
        """Lấy một câu trả lời (xoay vòng theo index). Mặc định câu đầu tiên.

        Gợi ý: dùng index % len(responses); nếu rỗng trả về "".
        """
        if not self._responses:
            return ""

        if len(self._responses) == 1:
            return self._responses[0]

        choices = [r for r in self._responses if r != self._last]
        ans = random.choice(choices)
        self._last = ans
        return ans

class KnowledgeBase:
    """Tập hợp các Intent, có thể nạp từ tệp JSON."""

    def __init__(self, intents=None, metadata=None):
        self._intents = list(intents) if intents is not None else []
        self._metadata = dict(metadata) if metadata is not None else {}

    @property
    def intents(self):
        return self._intents

    @property
    def metadata(self):
        return self._metadata

    def __len__(self):
        return len(self._intents)

    @classmethod
    def load_json(cls, path):
        """Nạp kho tri thức từ JSON. Ném KnowledgeBaseError nếu có sự cố.

        Gợi ý:
          - Mở tệp với encoding='utf-8', dùng json.load.
          - Bắt FileNotFoundError và json.JSONDecodeError -> raise KnowledgeBaseError(...)
          - Nếu data thiếu khoá 'intents' -> raise KnowledgeBaseError(...)
          - Với mỗi phần tử, tạo Intent(tag, patterns, responses).
          - Trả về cls(intents, data.get('metadata', {})).
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        except FileNotFoundError:
            raise KnowledgeBaseError(f"Không tìm thấy tệp: {path}")

        except json.JSONDecodeError as e:
            raise KnowledgeBaseError(f"JSON không hợp lệ: {e}")

        if "intents" not in data:
            raise KnowledgeBaseError("Thiếu khóa 'intents' trong JSON")

        intents = []

        for item in data["intents"]:
            intent = Intent(
                item["tag"],
                item.get("patterns", []),
                item.get("responses", [])
            )
            intents.append(intent)

        return cls(intents, data.get("metadata", {}))

    def find_best(self, user_text):
        """Tìm intent khớp nhất. Trả về (intent, score); (None, 0.0) nếu không khớp.

        Gợi ý: tokens = set(tokenize(user_text)); duyệt mọi intent, giữ điểm cao nhất.
        """
        user_tokens = set(tokenize(user_text))

        best_intent = None
        best_score = 0.0

        for intent in self._intents:
            score = intent.score(user_tokens)

            if score > best_score:
                best_score = score
                best_intent = intent

        return best_intent, best_score


# --------------------------------------------------------------------------- #
# PHẦN C — Kỹ năng (Skill) + Đa hình / Kế thừa (Bài 5)
# --------------------------------------------------------------------------- #
class Skill(abc.ABC):
    """Lớp TRỪU TƯỢNG: mọi kỹ năng phải tự cài đặt handle(). (Giữ nguyên)"""

    name = "skill"

    @abc.abstractmethod
    def handle(self, text):
        """Trả câu trả lời (str) nếu xử lý được, ngược lại None để nhường skill khác."""
        


class FaqSkill(Skill):
    """Trả lời câu hỏi thường gặp dựa trên KnowledgeBase + ngưỡng tin cậy."""

    name = "faq"

    def __init__(self, kb, threshold=DEFAULT_THRESHOLD):
        self._kb = kb
        self._threshold = threshold

    def handle(self, text):
        """Gợi ý: dùng kb.find_best(text); chỉ trả lời khi intent khác None VÀ
        score >= threshold; ngược lại trả về None."""
        intent, score = self._kb.find_best(text)

        if intent is not None and score >= self._threshold:
            return intent.reply()

        return None


def is_number(token):
    """Kiểm tra một chuỗi có biểu diễn được thành số hay không.

    Gợi ý: thử float(token) trong try/except ValueError.
    """
    try:
        float(token)
        return True
    except ValueError:
        return False


class MathSkill(Skill):
    """Tính biểu thức 'a op b', op ∈ {+, -, *, /}, cách nhau bởi dấu cách."""

    name = "math"
    OPS = {"+", "-", "*", "/"}

    def handle(self, text):
        """Gợi ý:
          - parts = text.strip().split(); nếu len != 3 -> None.
          - Nếu op không thuộc OPS hoặc a/b không phải số -> None.
          - Tính kết quả bằng if/elif; chia 0 thì trả "Không thể chia cho 0!".
          - Nếu kết quả là số nguyên (r == int(r)) thì hiển thị dạng int.
          - Trả chuỗi dạng: "a op b = r"
        """
        parts = text.strip().split()

        if len(parts) != 3:
            return None

        a, op, b = parts

        if op not in self.OPS:
            return None

        if not is_number(a) or not is_number(b):
            return None

        a = float(a)
        b = float(b)

        if op == "+":
            r = a + b
        elif op == "-":
            r = a - b
        elif op == "*":
            r = a * b
        elif op == "/":
            if b == 0:
                return "Không thể chia cho 0!   "
            r = a / b

        a = int(a) if a == int(a) else a
        b = int(b) if b == int(b) else b
        r = int(r) if r == int(r) else r

        return f"{a} {op} {b} = {r}"
    
class TimeSkill(Skill):
    name = "time"

    def handle(self, text):
        text = normalize(text)

        if text in [
            "may gio roi",
            "gio hien tai",
            "bay gio la may gio"
        ]:
            return "Bây giờ là " + datetime.now().strftime("%H:%M:%S")

        return None
    
class HelpSkill(Skill):
    name = "help"

    def handle(self, text):
        text = normalize(text)

        if text in ["help", "tro giup", "ban lam duoc gi"]:
            return (
                "Tôi có thể:\n"
                "- Trả lời FAQ\n"
                "- Tính toán (+ - * /)\n"
                "- Cho biết giờ hiện tại"
            )

        return None


# --------------------------------------------------------------------------- #
# PHẦN D — Trợ lý + Nhật ký hội thoại (Bài 5 + Bài 6)
# --------------------------------------------------------------------------- #
class Assistant:
    """Điều phối nhiều Skill theo thứ tự; ghi lại lịch sử hội thoại."""

    def __init__(self, skills, fallback=FALLBACK):
        self._skills = list(skills)
        self._fallback = fallback
        self._history = []

    @property
    def history(self):
        return self._history

    def respond(self, text):
        """Hỏi lần lượt từng skill; skill nào trả khác None thì dùng, hết thì fallback.

        Nhớ ghi vào _history: ('user', text) trước, rồi ('bot', câu_trả_lời).
        """
        self._history.append(("user", text))

        for skill in self._skills:
            response = skill.handle(text)
            if response is not None:
                self._history.append(("bot", response))
                return response

        self._history.append(("bot", self._fallback))
        return self._fallback

    def stats(self):
        """Trả dict {'messages': .., 'answered': .., 'fallback': ..}.

        - messages: số lượt role == 'user'
        - fallback: số lượt bot trả đúng câu _fallback
        - answered: số lượt bot trả lời - fallback
        """
        messages = sum(1 for role, _ in self._history if role == "user")
        fallback = sum(
            1 for role, text in self._history
            if role == "bot" and text == self._fallback
        )
        answered = messages - fallback

        return {
            "messages": messages,
            "answered": answered,
            "fallback": fallback
        }

    def reset(self):
        self._history.clear()

    def save_log(self, path):
        """Ghi hội thoại ra tệp UTF-8, mỗi dòng dạng 'Bạn: ...' hoặc 'Trợ lý: ...'."""
        with open(path, "w", encoding="utf-8") as f:
            for role, text in self._history:
                if role == "user":
                    f.write(f"Bạn: {text}\n")
                else:
                    f.write(f"Trợ lý: {text}\n")


# --------------------------------------------------------------------------- #
# PHẦN E — Giao diện dòng lệnh (ĐÃ VIẾT SẴN — không bắt buộc sửa)
# --------------------------------------------------------------------------- #
def build_assistant(kb_path, threshold=DEFAULT_THRESHOLD):
    """Tạo Assistant với 2 kỹ năng: ưu tiên MathSkill, sau đó FaqSkill."""
    kb = KnowledgeBase.load_json(kb_path)
    return Assistant([MathSkill(), TimeSkill(), HelpSkill(), FaqSkill(kb, threshold)])


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Trợ lý hỏi-đáp theo luật")
    p.add_argument("--kb", default=os.path.join(HERE, "knowledge_base.json"),
                   help="Đường dẫn tệp tri thức JSON")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                   help="Ngưỡng tin cậy để trả lời (0..1)")
    return p.parse_args(argv)


HELP_TEXT = """Lệnh đặc biệt:
  /help    : hiện trợ giúp
  /stats   : xem thống kê hội thoại
  /save    : lưu nhật ký ra chat_log.txt
  /reset   : xoá lịch sử
  /quit    : thoát
Hoặc cứ gõ câu hỏi bất kỳ (vd: 'mật khẩu wifi', '12 + 30')."""


def chat_loop(assistant):
    print("=== Trợ lý Khoa CNTT (gõ /help để xem lệnh, /quit để thoát) ===")
    while True:
        try:
            text = input("Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTạm biệt!")
            break
        if not text:
            continue
        if text == "/quit":
            print("Trợ lý: Tạm biệt bạn!")
            break
        elif text == "/help":
            print(HELP_TEXT)
        elif text == "/stats":
            print("Trợ lý:", assistant.stats())
        elif text == "/save":
            path = os.path.join(HERE, "chat_log.txt")
            assistant.save_log(path)
            print(f"Trợ lý: Đã lưu nhật ký vào {path}")
        elif text == "/reset":
            assistant.reset()
            print("Trợ lý: Đã xoá lịch sử hội thoại.")
        else:
            print("Trợ lý:", assistant.respond(text))


def main(argv=None):
    args = parse_args(argv)
    try:
        assistant = build_assistant(args.kb, args.threshold)
    except KnowledgeBaseError as e:
        print(f"[LỖI] {e}")
        return 1
    chat_loop(assistant)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
