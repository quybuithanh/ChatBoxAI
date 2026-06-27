# Câu 1:

    - Khi không có intent nào phù hợp với câu hỏi của người dùng thì nên trả về (None, 0.0), vì:
    + Tránh đưa ra những câu trả lời không đúng ngữ cảnh với câu hỏi của người dùng, dễ gây ra khó hiểu, làm giảm trải nghiệm sử dụng cho người dùng.
    - Do đó, khi trả về (None, 0.0) thì Assistant sử dụng câu trả lời mặc định (fallback).

# Câu 2:

    - Khi thử với câu "bạn ăn cơm chưa", chatbot của em trả lời theo intent greeting.
    - Nguyên nhân là hàm keyword_score chỉ tính số lượng từ khóa trùng nhau giữa câu hỏi của người dùng và mẫu câu của từng intent.
    - Vì 2 câu có chung từ "bạn" nên điểm khớp = 0.5 trùng với giá trị mặc định của threshold nên chatbot xem đây là một câu chào và trả lời theo intent greeting.
    - Cách sửa:
    + Loại bỏ những từ xuất hiện rất nhiều nhưng ít mang ý nghĩa cụ thể ví dụ ("bạn", "mình", "cho", "với"...)
    + Tăng giá trị threshold để chatbot chỉ trả lời khi mức độ khớp đủ cao để tăng tỉ lệ câu trả lời của chatbot trùng khớp với câu hỏi người dùng.

# Câu 3:

    - Assistant sẽ gọi từng Skill theo đúng thứ tự trong danh sách. Skill nào xử lý được sẽ trả về kết quả ngay và các skill phía sau sẽ không gọi nữa.
    - MathSkill được đặt trước FaqSkill để các biểu thức tính toán được tính toán trước và trả kết quả ngay.
    - Nếu đặt FaqSkill lên trước, biểu thức toán học có thể bị khớp nhầm với một intent nào đó nếu chúng có từ khóa giống nhau. Khi đó chatbot sẽ trả về câu trả lời FAQ thay vì thực hiện phép tính.

# Câu 4:

    - Strip_accents dùng để loại bỏ dấu của tiếng Việt trước khi so sánh.
    - Vì vậy, chatbot vẫn nhận diện đúng ý định của người dùng mà không cần quan tâm đến việc câu có dấu hoặc không dấu.
