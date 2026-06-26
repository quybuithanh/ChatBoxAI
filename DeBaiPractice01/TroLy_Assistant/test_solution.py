"""
Bộ kiểm thử cho solution.py — chạy: python3 test_solution.py
In "ALL TESTS PASSED" nếu mọi assert đúng.

Mỗi nhóm test ứng với một bài trong Module 1:
  A. Xử lý chuỗi (Bài 2/3/4)   : strip_accents, normalize, tokenize, keyword_score
  B. Intent & KnowledgeBase     : score, find_best, load_json, bắt lỗi tệp (Bài 5/6)
  C. Skill + đa hình            : Skill trừu tượng, FaqSkill, MathSkill (Bài 5)
  D. Assistant + File I/O       : respond/history/stats/save_log (Bài 5/6)
"""

import json
import os
import tempfile

import solution as S
from solution import (Intent, KnowledgeBase, KnowledgeBaseError, Skill,
                      FaqSkill, MathSkill, Assistant)


def sample_kb():
    """KB nhỏ, cố định để test khỏi phụ thuộc tệp ngoài."""
    return KnowledgeBase([
        Intent("greeting", ["xin chào", "chào bạn", "hello", "hi"],
               ["Xin chào!", "Chào bạn!"]),
        Intent("hours", ["mấy giờ mở cửa", "giờ làm việc", "thời gian làm việc"],
               ["Mở cửa 7h–21h."]),
        Intent("wifi", ["mật khẩu wifi", "wifi password", "pass wifi"],
               ["Mật khẩu wifi là OU@2026."]),
    ], metadata={"name": "test-kb"})


# ----- A. XỬ LÝ CHUỖI -------------------------------------------------------
def test_strip_accents():
    assert S.strip_accents("Chào Đại học Mở") == "Chao Dai hoc Mo"
    assert S.strip_accents("Tiếng Việt") == "Tieng Viet"
    assert S.strip_accents("Python") == "Python"
    print("  [OK] test_strip_accents")


def test_normalize_and_tokenize():
    assert S.normalize("Chào Bạn!!!   ") == "chao ban"
    assert S.normalize("Wi-Fi của Khoa?") == "wi fi cua khoa"
    assert S.normalize("   ") == ""
    assert S.tokenize("Mấy giờ mở cửa?") == ["may", "gio", "mo", "cua"]
    assert S.tokenize("") == []
    print("  [OK] test_normalize_and_tokenize")


def test_keyword_score():
    assert S.keyword_score({"a", "b", "c"}, {"a", "b"}) == 1.0
    assert S.keyword_score({"a"}, {"a", "b"}) == 0.5
    assert S.keyword_score(set(), {"a"}) == 0.0
    assert S.keyword_score({"x"}, set()) == 0.0          # mẫu rỗng -> 0
    # Nhận cả list (tự ép sang set bên trong)
    assert S.keyword_score(["a", "a", "b"], ["a", "b"]) == 1.0
    print("  [OK] test_keyword_score")


# ----- B. INTENT & KNOWLEDGEBASE -------------------------------------------
def test_intent_score_and_reply():
    it = Intent("greeting", ["xin chào", "hello"], ["A", "B"])
    toks = set(S.tokenize("xin chào trợ lý ơi"))
    assert it.score(toks) == 1.0                          # khớp trọn mẫu "xin chào"
    assert it.score(set(S.tokenize("hôm nay trời đẹp"))) == 0.0
    assert it.reply(0) == "A" and it.reply(1) == "B"
    assert it.reply(2) == "A"                             # xoay vòng
    assert it.tag == "greeting" and it.patterns == ["xin chào", "hello"]
    print("  [OK] test_intent_score_and_reply")


def test_kb_find_best():
    kb = sample_kb()
    assert len(kb) == 3
    intent, score = kb.find_best("cho mình hỏi mật khẩu wifi với")
    assert intent.tag == "wifi" and score >= 0.5
    intent, score = kb.find_best("phòng mình mấy giờ mở cửa vậy")
    assert intent.tag == "hours"
    # Câu vô nghĩa -> không khớp gì
    intent, score = kb.find_best("zzz qqq lorem ipsum")
    assert intent is None and score == 0.0
    print("  [OK] test_kb_find_best")


def test_kb_load_json_roundtrip():
    data = {
        "metadata": {"name": "demo"},
        "intents": [
            {"tag": "hi", "patterns": ["xin chào"], "responses": ["chào"]},
            {"tag": "bye", "patterns": ["tạm biệt"], "responses": ["bye"]},
        ],
    }
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "kb.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        kb = KnowledgeBase.load_json(path)
    assert len(kb) == 2
    assert [it.tag for it in kb.intents] == ["hi", "bye"]
    assert kb.metadata["name"] == "demo"
    print("  [OK] test_kb_load_json_roundtrip")


def test_kb_load_errors():
    # 1) Tệp không tồn tại
    try:
        KnowledgeBase.load_json("khong_co_tep_nay_12345.json")
        raised = False
    except KnowledgeBaseError:
        raised = True
    assert raised, "Phải ném KnowledgeBaseError khi tệp không tồn tại"

    with tempfile.TemporaryDirectory() as d:
        # 2) JSON hỏng
        bad = os.path.join(d, "bad.json")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("{ khong phai json hop le ")
        try:
            KnowledgeBase.load_json(bad)
            raised = False
        except KnowledgeBaseError:
            raised = True
        assert raised, "Phải ném KnowledgeBaseError khi JSON hỏng"

        # 3) Thiếu khoá 'intents'
        miss = os.path.join(d, "miss.json")
        with open(miss, "w", encoding="utf-8") as f:
            json.dump({"metadata": {}}, f)
        try:
            KnowledgeBase.load_json(miss)
            raised = False
        except KnowledgeBaseError:
            raised = True
        assert raised, "Phải ném KnowledgeBaseError khi thiếu 'intents'"
    print("  [OK] test_kb_load_errors")


# ----- C. SKILL + ĐA HÌNH ---------------------------------------------------
def test_skill_is_abstract_and_polymorphic():
    assert issubclass(FaqSkill, Skill) and issubclass(MathSkill, Skill)
    # Không khởi tạo trực tiếp lớp trừu tượng
    try:
        Skill()
        raised = False
    except TypeError:
        raised = True
    assert raised, "Skill phải là lớp TRỪU TƯỢNG"
    # Mỗi lớp con tự cài handle() (đa hình thực sự)
    assert FaqSkill.handle is not Skill.handle
    assert MathSkill.handle is not FaqSkill.handle
    print("  [OK] test_skill_is_abstract_and_polymorphic")


def test_math_skill():
    m = MathSkill()
    assert m.handle("12 + 30") == "12 + 30 = 42"
    assert m.handle("10 / 4") == "10 / 4 = 2.5"
    assert m.handle("6 * 7") == "6 * 7 = 42"
    assert "0" in m.handle("5 / 0")              # thông báo chia 0
    assert m.handle("xin chào") is None          # không phải phép tính
    assert m.handle("2 ^ 3") is None             # toán tử không hỗ trợ
    print("  [OK] test_math_skill")


def test_faq_skill_threshold():
    kb = sample_kb()
    faq = FaqSkill(kb, threshold=0.5)
    assert faq.handle("xin chào") in ["Xin chào!", "Chào bạn!"]
    assert faq.handle("zzz qqq vô nghĩa") is None
    print("  [OK] test_faq_skill_threshold")


# ----- D. ASSISTANT + FILE I/O ---------------------------------------------
def test_assistant_respond_and_history():
    kb = sample_kb()
    bot = Assistant([MathSkill(), FaqSkill(kb)])
    assert bot.respond("xin chào") in ["Xin chào!", "Chào bạn!"]
    assert bot.respond("3 * 4") == "3 * 4 = 12"
    assert bot.respond("zzz qqq") == S.FALLBACK
    # Lịch sử: 3 lượt user + 3 lượt bot, xen kẽ đúng vai
    assert len(bot.history) == 6
    roles = [role for role, _ in bot.history]
    assert roles == ["user", "bot", "user", "bot", "user", "bot"]
    print("  [OK] test_assistant_respond_and_history")


def test_assistant_stats_and_save_log():
    kb = sample_kb()
    bot = Assistant([MathSkill(), FaqSkill(kb)])
    bot.respond("xin chào")     # answered
    bot.respond("3 * 4")        # answered
    bot.respond("zzz qqq")      # fallback
    assert bot.stats() == {"messages": 3, "answered": 2, "fallback": 1}

    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "log.txt")
        bot.save_log(path)
        assert os.path.exists(path)
        content = open(path, encoding="utf-8").read()
    lines = [ln for ln in content.splitlines() if ln.strip()]
    assert len(lines) == 6
    assert any(ln.startswith("Trợ lý:") for ln in lines)
    assert any(ln.startswith("Bạn:") for ln in lines)
    print("  [OK] test_assistant_stats_and_save_log")


def test_encapsulation():
    it = Intent("t", ["a"], ["r"])
    assert hasattr(it, "_patterns") and hasattr(it, "_responses")
    assert it.tag == "t" and it.responses == ["r"]
    print("  [OK] test_encapsulation")


def main():
    tests = [
        test_strip_accents,
        test_normalize_and_tokenize,
        test_keyword_score,
        test_intent_score_and_reply,
        test_kb_find_best,
        test_kb_load_json_roundtrip,
        test_kb_load_errors,
        test_skill_is_abstract_and_polymorphic,
        test_math_skill,
        test_faq_skill_threshold,
        test_assistant_respond_and_history,
        test_assistant_stats_and_save_log,
        test_encapsulation,
    ]
    print(f"Chạy {len(tests)} bài kiểm thử...\n")
    for t in tests:
        t()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
