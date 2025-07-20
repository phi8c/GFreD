# app/controllers/exam_controller.py

from models.exam_model import get_all_questions, create_exam_code, save_exam_question, get_questions_by_exam_set
import random

def shuffle_exam_versions(user_id, exam_set_id, num_versions):
    # questions = get_all_questions()
    questions = get_questions_by_exam_set(user_id, exam_set_id)

    for i in range(1, num_versions + 1):
        exam_code = f"{exam_set_id}-{i:03}"  # Ví dụ: 5-001  # mã đề 001, 002, ...
        exam_code_id = create_exam_code(exam_code, exam_set_id)

        # Trộn thứ tự câu hỏi
        shuffled_questions = questions.copy()
        random.shuffle(shuffled_questions)

        for order, q in enumerate(shuffled_questions, start=1):
            # Trộn đáp án
            options = [q["answer_a"], q["answer_b"], q["answer_c"], q["answer_d"]]
            correct_text = q["correct_answer"]

            paired = list(zip(["A", "B", "C", "D"], options))
            random.shuffle(paired)
            new_labels, new_options = zip(*paired)

            # Tìm đáp án đúng mới
            # new_correct = next(
            #     opt for label, opt in paired if opt == correct_text
            # )
            # Xác định đáp án đúng sau shuffle
            new_correct_label = None
            for label, option in paired:
                if option == correct_text:
                    new_correct_label = label
                    break

            if new_correct_label is None:
                print(f"🚨 Không tìm được đáp án đúng sau shuffle cho câu hỏi ID {q['id']}")
                continue

            # Các câu hỏi đơn thuần: chapter, difficulty = None

            save_exam_question(
                exam_code_id,
                q["id"],
                order,
                new_options,
                new_correct_label,
                chapter=None,
                difficulty=None
            )
def shuffle_advanced_exam_versions(user_id, exam_set_id, num_versions):
    questions = get_questions_by_exam_set(user_id, exam_set_id)

    if not questions:
        print("🚨 Không tìm thấy câu hỏi cho bộ đề này!")
        return

    for i in range(1, num_versions + 1):
        exam_code = f"{exam_set_id}-{i:03}"  # Ví dụ: 5-001
        exam_code_id = create_exam_code(exam_code, exam_set_id)

        shuffled_questions = questions.copy()
        random.shuffle(shuffled_questions)

        for order, q in enumerate(shuffled_questions, start=1):
            #options = [q["answer_a"], q["answer_b"], q["answer_c"], q["answer_d"]]
            
            correct_label = q["correct_answer"]  # "A", "B", "C", "D"
            correct_text = q.get(f"answer_{correct_label.lower()}")  # Lấy nội dung đáp án đúng

            # Tiến hành shuffle đáp án
            paired = list(zip(["A", "B", "C", "D"], [q["answer_a"], q["answer_b"], q["answer_c"], q["answer_d"]]))
            random.shuffle(paired)
            new_labels, new_options = zip(*paired)

            # Tìm lại label mới của đáp án đúng
            new_correct_label = None
            for label, option in paired:
             if option == correct_text:
              new_correct_label = label
              break


            if new_correct_label is None:
                print(f"🚨 Không tìm được đáp án đúng sau shuffle cho câu hỏi ID {q['id']}")
                continue

            # Các câu hỏi nâng cao: lấy chapter và difficulty thật sự
            save_exam_question(
                exam_code_id,
                q["id"],
                order,
                new_options,
                new_correct_label,
                chapter=q.get("chapter"),
                difficulty=q.get("difficulty")
            )


