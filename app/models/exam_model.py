# app/models/exam_model.py

import random
from gen_questions import get_db_connection
import string
from datetime import datetime



def generate_room_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def create_exam_room(subject_name, duration_minutes, user_id, exam_set_id, open_time, grace_period_minutes, easy_percentage=None, medium_percentage=None, hard_percentage=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    room_code = generate_room_code()
    
    
    
    # query = "INSERT INTO exam_rooms (room_code, subject_name, duration_minutes, created_by_user_id, exam_set_id, open_time, grace_period_minutes, difficulty_easy_pct, difficulty_medium_pct, difficulty_hard_pct) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    # cursor.execute(query, (room_code, subject_name, duration_minutes,user_id, exam_set_id, open_time, grace_period_minutes, easy_percentage, medium_percentage, hard_percentage))

    # conn.commit()
    # cursor.close()
    # conn.close()

    # return room_code
    
    # Nếu đủ thông tin phân bổ độ khó (nghĩa là bộ đề nâng cao)
    if easy_percentage is not None and medium_percentage is not None and hard_percentage is not None:
        query = """
            INSERT INTO exam_rooms 
            (room_code, subject_name, duration_minutes, created_by_user_id, exam_set_id,
             open_time, grace_period_minutes, difficulty_easy_pct, difficulty_medium_pct, difficulty_hard_pct)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            room_code, subject_name, duration_minutes, user_id, exam_set_id,
            open_time, grace_period_minutes, easy_percentage, medium_percentage, hard_percentage
        ))
    else:
        # Bộ đề thường, không có phân bổ độ khó
        query = """
            INSERT INTO exam_rooms 
            (room_code, subject_name, duration_minutes, created_by_user_id, exam_set_id,
             open_time, grace_period_minutes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            room_code, subject_name, duration_minutes, user_id, exam_set_id,
            open_time, grace_period_minutes
        ))

    conn.commit()
    cursor.close()
    conn.close()

    return room_code

def get_all_questions():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM questions ")
    questions = cursor.fetchall()
    cursor.close()
    conn.close()
    return questions

def create_exam_code(code, exam_set_id): # updated!!
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO exam_codes (code, exam_set_id) VALUES (%s, %s)", (code, exam_set_id))
    conn.commit()
    exam_code_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return exam_code_id






def save_exam_question(exam_code_id, question_id, order, shuffled_answers, correct_answer, chapter=None, difficulty=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO exam_question_map (
            exam_code_id, question_id, question_order,
            answer_a, answer_b, answer_c, answer_d,
            correct_answer,
            chapter, difficulty
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (
        exam_code_id,
        question_id,
        order,
        shuffled_answers[0],
        shuffled_answers[1],
        shuffled_answers[2],
        shuffled_answers[3],
        correct_answer,
        chapter,
        difficulty
    ))
    conn.commit()
    cursor.close()
    conn.close()

def assign_exam_code(room_code, exam_set_id):
    # Lấy danh sách sinh viên đã đăng ký trong phòng
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) 
        FROM student_exams 
        WHERE room_code = %s AND exam_set_id = %s
    """, (room_code, exam_set_id))
    count = cursor.fetchone()[0]

    # Danh sách mã đề thuộc bộ đề này (chỉ lấy mã đề có exam_set_id tương ứng)
    cursor.execute("""
        SELECT code FROM exam_codes
        WHERE exam_set_id = %s ORDER BY code
    """, (exam_set_id,))
    available_codes = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    if not available_codes:
        raise ValueError("❌ Không có mã đề nào được tạo cho bộ đề này!")

    # Gán mã đề theo lượt để tránh trùng (xoay vòng theo số lượng mã đề)
    assigned_code = available_codes[count % len(available_codes)]
    return assigned_code
def get_exam_questions_by_code(exam_code_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Lấy câu hỏi MCQ từ exam_question_map
    cursor.execute("""
        SELECT eqm.*, q.question_text
        FROM exam_question_map eqm
        JOIN questions q ON eqm.question_id = q.id
        WHERE eqm.exam_code_id = %s
        ORDER BY eqm.question_order
    """, (exam_code_id,))
    mcq_questions = cursor.fetchall()

    # Lấy câu hỏi TF từ hs_question_map
    cursor.execute("""
        SELECT hqm.id AS map_id, hqm.original_question_id, hqm.position, tf.*
        FROM hs_question_map hqm
        JOIN tf_questions tf ON tf.id = hqm.original_question_id
        WHERE hqm.exam_code_id = %s AND hqm.question_type = 'tf'
        ORDER BY hqm.position
    """, (exam_code_id,))
    tf_questions_raw = cursor.fetchall()

    tf_questions = []
    for q in tf_questions_raw:
        cursor.execute("""
            SELECT label, content, is_true, position
            FROM hs_tf_statements
            WHERE hs_map_id = %s
            ORDER BY position
        """, (q['map_id'],))
        statements = cursor.fetchall()
        q['statements'] = statements
        tf_questions.append(q)

    # Lấy câu hỏi SA từ hs_question_map
    cursor.execute("""
        SELECT hqm.position, sa.*
        FROM hs_question_map hqm
        JOIN short_answer_questions sa ON sa.id = hqm.original_question_id
        WHERE hqm.exam_code_id = %s AND hqm.question_type = ' '
        ORDER BY hqm.position
    """, (exam_code_id,))
    sa_questions = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        'mcq': mcq_questions,
        'tf': tf_questions,
        'sa': sa_questions
    }
    
def get_exam_mcq_questions_by_code(exam_code_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            eqm.question_order,
            q.question_text,
            eqm.answer_a,
            eqm.answer_b,
            eqm.answer_c,
            eqm.answer_d,
            eqm.correct_answer
        FROM exam_question_map eqm
        JOIN questions q ON eqm.question_id = q.id
        WHERE eqm.exam_code_id = %s
        ORDER BY eqm.question_order
    """
    cursor.execute(query, (exam_code_id,))
    questions = cursor.fetchall()

    cursor.close()
    conn.close()
    return questions


# hàm này mới thêm vào


def is_thpt2025_exam_set(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Kiểm tra có tồn tại câu hỏi TF hoặc SA thuộc exam_set_id không
    tf_query = "SELECT 1 FROM tf_questions WHERE exam_set_id = %s LIMIT 1"
    sa_query = "SELECT 1 FROM short_answer_questions WHERE exam_set_id = %s LIMIT 1"

    cursor.execute(tf_query, (exam_set_id,))
    is_tf = cursor.fetchone() is not None

    cursor.execute(sa_query, (exam_set_id,))
    is_sa = cursor.fetchone() is not None

    cursor.close()
    conn.close()

    return is_tf or is_sa

def get_exam_code_id_by_code(code) :
    
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT id FROM exam_codes WHERE code = %s LIMIT 1"

    try:
        cursor.execute(query, (code,))
        result = cursor.fetchone()

        if result:
            return result[0]  # Trả về ID (là phần tử đầu tiên của tuple)
        else:
            return None       # Không tìm thấy mã đề
    except Exception as e:
        print(f"Lỗi khi lấy exam_code_id cho code '{code}': {e}")
        return None
    finally:
        cursor.close()
        conn.close()
def get_student_code_by_exam_and_room(student_exam_id, room_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT student_code
        FROM student_exams
        WHERE id = %s AND room_code = %s
        LIMIT 1
    """

    try:
        cursor.execute(query, (student_exam_id, room_code))
        result = cursor.fetchone()

        if result:
            return result[0]  # Trả về student_code
        else:
            return None       # Không tìm thấy kết quả phù hợp
    except Exception as e:
        print(f"Lỗi khi lấy student_code với student_exam_id '{student_exam_id}' và room_code '{room_code}': {e}")
        return None
    finally:
        cursor.close()
        conn.close()
        

        



#  này kết thúc

def get_original_questions_thpt2025(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy MCQ
    cursor.execute("""
        SELECT id, 'MCQ' AS type, question_text, answer_a, answer_b, answer_c, answer_d, correct_answer
        FROM questions
        WHERE exam_set_id = %s
        ORDER BY id
    """, (exam_set_id,))
    mcq = cursor.fetchall()
    print("== MCQ FETCHED FROM DB =", mcq)

    # Lấy TF
    cursor.execute("""
        SELECT tf.id, 'tf' AS question_type, tf.question_text, ti.statement_text, ti.is_true, tf.image_url
        FROM tf_questions tf
        JOIN tf_items ti ON tf.id = ti.tf_question_id
        WHERE tf.exam_set_id = %s
        ORDER BY tf.id, ti.id
    """, (exam_set_id,))
    tf_raw = cursor.fetchall()

    tf_dict = {}
    for item in tf_raw:
        qid = item['id']
        if qid not in tf_dict:
            tf_dict[qid] = {
                'question_type': 'tf',
                'question_text': item['question_text'],
                'image_url': item.get('image_url'),
                'sub_items': []
            }
        tf_dict[qid]['sub_items'].append({
            'statement_text': item['statement_text'],
            'is_true': item['is_true']
        })
    tf = list(tf_dict.values())

    # Lấy SA
    cursor.execute("""
        SELECT id, 'SA' AS question_type, question_text, correct_answer
        FROM short_answer_questions
        WHERE exam_set_id = %s
        ORDER BY id
    """, (exam_set_id,))
    sa = cursor.fetchall()
    print("== SA FETCHED FROM DB =", sa)

    cursor.close()
    conn.close()

    return {
        'MCQ': mcq,
        'tf': tf,
        'SA': sa
    }
    
def get_exam_questions_by_code_id(exam_code_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            eqm.question_id,
            eqm.question_order,
            eqm.answer_a,
            eqm.answer_b,
            eqm.answer_c,
            eqm.answer_d,
            eqm.correct_answer,
            q.question_text
        FROM exam_question_map eqm
        JOIN questions q ON eqm.question_id = q.id
        WHERE eqm.exam_code_id = %s
        ORDER BY eqm.question_order
    """, (exam_code_id,))

    mcq_questions = cursor.fetchall()

    cursor.close()
    conn.close()

    return mcq_questions

    
    
    
   


    
    


   

    


def save_student_submission(student_code, student_name, exam_code, room_code, answers, score):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Lưu vào bảng submissions
    cursor.execute("""
        INSERT INTO submissions (student_code, student_name, exam_code, room_code, score)
        VALUES (%s, %s, %s, %s, %s)
    """, (student_code, student_name, exam_code, room_code, score))
    submission_id = cursor.lastrowid

    # Lưu từng câu trả lời
    for question_id, selected_answer in answers.items():
        cursor.execute("""
            INSERT INTO submission_answers (submission_id, question_id, selected_answer)
            VALUES (%s, %s, %s)
        """, (submission_id, question_id, selected_answer))

    conn.commit()
    cursor.close()
    conn.close()
def save_student_exam(student_name, student_code, room_code, exam_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO student_exams (student_name, student_code, room_code, exam_code, submitted, score, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    submitted = False
    score = 0  # sẽ cập nhật sau khi nộp
    created_at = datetime.now()

    cursor.execute(query, (student_name, student_code, room_code, exam_code, submitted, score, created_at))
    conn.commit()

    student_exam_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return student_exam_id


def get_student_exam_id(student_code, room_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT id AS student_exam_id
        FROM student_exams
        WHERE student_code = %s AND room_code = %s
        LIMIT 1
    """
    cursor.execute(query, (student_code, room_code))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result:
        return result['student_exam_id']
    else:
        return None  # hoặc raise Exception nếu muốn xử lý cứng


def save_student_answer(student_exam_id, question_id, selected_answer, is_correct):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 🔍 Truy ngược từ student_exam_id để lấy student_id, exam_room_id, exam_code
    cursor.execute("""
        SELECT s.id AS student_id, r.id AS exam_room_id, e.exam_code
        FROM student_exams e
        JOIN students s ON e.student_code = s.student_id
        JOIN exam_rooms r ON r.room_code = e.room_code
        WHERE e.id = %s
    """, (student_exam_id,))
    
    result = cursor.fetchone()
    if not result:
        cursor.close()
        conn.close()
        raise ValueError("❌ Không tìm thấy thông tin phiên làm bài.")

    submitted_at = datetime.now()

    # ✅ Lưu bài làm
    cursor.execute("""
        INSERT INTO student_exam_submissions
        (student_id, exam_room_id, exam_code, question_id, selected_answer, is_correct, submitted_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        result['student_id'],
        result['exam_room_id'],
        result['exam_code'],
        question_id,
        selected_answer,
        is_correct,
        submitted_at
    ))

    conn.commit()
    cursor.close()
    conn.close()
    
    



def get_correct_answer(question_id, exam_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT correct_answer 
        FROM exam_question_map 
        WHERE question_id = %s AND exam_code_id = %s
    """, (question_id, exam_code))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else ""
def update_student_exam_score(student_code, room_code, score):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        UPDATE student_exams
        SET score = %s, submitted = 1
        WHERE student_code = %s AND room_code = %s
    """
    cursor.execute(query, (score, student_code, room_code))
    conn.commit()

    cursor.close()
    conn.close()
def get_exam_sets(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT DISTINCT es.id, es.set_name
        FROM exam_sets es
        JOIN exam_codes ec ON ec.exam_set_id = es.id
        WHERE es.user_id = %s
    """
    cursor.execute(query, (user_id,))
    exam_sets = cursor.fetchall()

    cursor.close()
    conn.close()
    return exam_sets

def get_exam_code_id_by_code(code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM exam_codes WHERE code = %s", (code,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None



def get_exam_codes_by_set(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT code FROM exam_codes WHERE exam_set_id = %s ORDER BY code"
    cursor.execute(query, (exam_set_id,))
    result = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()
    return result
def get_questions_by_exam_set(user_id, exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT * FROM questions
        WHERE user_id = %s AND exam_set_id = %s
    """
    cursor.execute(query, (user_id, exam_set_id))
    questions = cursor.fetchall()
    cursor.close()
    conn.close()
    return questions
def check_exam_type(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT COUNT(*) 
        FROM questions
        WHERE exam_set_id = %s
        AND (chapter IS NOT NULL OR difficulty IS NOT NULL)
    """
    cursor.execute(query, (exam_set_id,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result and result[0] > 0:
        return "advanced"  # Có ít nhất 1 câu có chapter hoặc difficulty
    else:
        return "basic"  # Toàn bộ câu hỏi không có chapter và difficulty
def is_advanced_exam(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM exam_question_map
        WHERE exam_id = %s AND (difficulty IS NOT NULL OR chapter IS NOT NULL)
    """, (exam_set_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] > 0
def is_advanced_exam_set(exam_code_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.difficulty
        FROM exam_question_map eqm
        JOIN questions q ON eqm.question_id = q.id
        WHERE eqm.exam_code_id = %s
        LIMIT 1
    """, (exam_code_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result and result[0] is not None  # Nếu có difficulty thì là nâng cao
def sel_exam_code_id_by_code(exam_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM exam_codes WHERE code = %s", (exam_code,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None



def get_latest_exam_set_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id FROM exam_sets
        WHERE user_id = %s
        ORDER BY created_at DESC LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row["id"] if row else None
def get_room_id_by_code(room_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM exam_rooms WHERE room_code = %s", (room_code,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result["id"] if result else None
def get_original_questions_by_exam_set(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT id, question_text, difficulty
        FROM questions
        WHERE exam_set_id = %s
        ORDER BY id
    """
    cursor.execute(query, (exam_set_id,))
    questions = cursor.fetchall()

    cursor.close()
    conn.close()
    return questions

# ĐÂY LÀ NHỮNG HÀM MỚI THÊM VÀO 

def save_mcq_questions( questions, exam_set_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    for q in questions:
        try:
            cursor.execute("""
                INSERT INTO questions (
                    question_text, answer_a, answer_b, answer_c, answer_d,
                    correct_answer, user_id, exam_set_id, chapter, difficulty
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                q['question_text'],
                q['option_a'], q['option_b'], q['option_c'], q['option_d'],
                q['correct_answer'],
                user_id,
                exam_set_id,
                None,   # không lưu chapter
                None    # chưa có difficulty
            ))
        except Exception as e:
            print(f"❌ Lỗi khi lưu câu MCQ: {e}")
    conn.commit()
    cursor.close()
def save_tf_questions( tf_questions, exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    for q in tf_questions:
        cursor.execute("""
            INSERT INTO tf_questions (
                exam_set_id, question_text, image_url, created_at
            ) VALUES (%s, %s, %s, NOW())
        """, (exam_set_id, q['main_statement'], q.get('image_path')))
        
        tf_question_id = cursor.lastrowid

        for i, sub in enumerate(q['sub_statements']):
            cursor.execute("""
                INSERT INTO tf_items (
                    tf_question_id, statement_text, is_true, sort_order, created_at
                ) VALUES (%s, %s, %s, %s, NOW())
            """, (tf_question_id, sub['statement'], sub['is_true'], i))
    conn.commit()
    cursor.close()
def save_short_answer_questions( short_questions, exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    for q in short_questions:
        cursor.execute("""
            INSERT INTO short_answer_questions (
                exam_set_id, question_text, correct_answer, image_url, explanation, created_at
            ) VALUES (%s, %s, %s, %s, %s, NOW())
        """, (
            exam_set_id, q['question_text'], q['answer'],
            None, None
        ))
    conn.commit()
    cursor.close()



# KẾT THÚC HÀM MỚI THÊM VÀO

# hàm cập nhật mới thêm vào

def update_student_exam_score_scd(student_code, room_code, score): 
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        UPDATE student_exams
        SET 
            score = %s,
            submitted = 1,
            end_time = NOW(),
            status = 'submitted'
        WHERE 
            student_code = %s 
            AND room_code = %s
            AND submitted = 0  -- đảm bảo không cập nhật lại nếu đã nộp
    """
    cursor.execute(query, (score, student_code, room_code))
    conn.commit()

    cursor.close()
    conn.close()
    
    
    
def save_student_tf_submissions(tf_submissions):
    if not tf_submissions:
        print("❗Danh sách tf_submissions rỗng, không có gì để lưu.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    submitted_at = datetime.now()

    try:
        for item in tf_submissions:
            cursor.execute("""
                INSERT INTO student_tf_submissions 
                (student_id, exam_room_id, exam_code, map_id, statement_id, student_answer, is_correct, submitted_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                item['student_id'],
                item['exam_room_id'],
                item['exam_code'],
                item['map_id'],
                item['statement_id'],
                item['student_answer'],
                item['is_correct'],
                submitted_at
            ))
        
        conn.commit()
        print(f"✅ Đã lưu {len(tf_submissions)} dòng vào student_tf_submissions.")

    except Exception as e:
        conn.rollback()
        print("❌ Lỗi khi lưu tf_submissions:", str(e))
    
    finally:
        cursor.close()
        conn.close()


# hàm này mới thêm vào để lưu bài thi sinh viên


def save_mcq_sa_submissions_v2(student_exam_id, graded_answers):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 🔍 Truy ngược từ student_exam_id để lấy thông tin sinh viên + phòng thi
    cursor.execute("""
        SELECT s.id AS student_id, r.id AS exam_room_id, e.exam_code
        FROM student_exams e
        JOIN students s ON e.student_code = s.student_id
        JOIN exam_rooms r ON r.room_code = e.room_code
        WHERE e.id = %s
    """, (student_exam_id,))
    
    result = cursor.fetchone()
    if not result:
        cursor.close()
        conn.close()
        raise ValueError("❌ Không tìm thấy thông tin phiên làm bài.")

    submitted_at = datetime.now()

    insert_query = """
        INSERT INTO student_exam_submissions
        (student_id, exam_room_id, exam_code, question_id, selected_answer, is_correct, submitted_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    for item in graded_answers:
        try:
            question_id = int(item['question_id'])
            answer = item['answer'] if item['answer'] is not None else ''
            is_correct = bool(item['is_correct'])

            cursor.execute(insert_query, (
                result['student_id'],
                result['exam_room_id'],
                result['exam_code'],
                question_id,
                answer,
                is_correct,
                submitted_at
            ))
        except Exception as e:
            print(f"⚠️ Lỗi khi lưu item: {item} → {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Đã lưu toàn bộ bài làm của sinh viên.")

# kết thúc hàm mới thêm vào để lưu bài thi sinh viên


# kết thúc hàm cập nhật mới thêm vào


# hàm cập nhật bài thi của sinh viên

def save_student_submissions(student_id, room_code, exam_code, graded_answers):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Lưu câu hỏi MCQ
    insert_query = """
        INSERT INTO student_exam_submissions
            (student_id, exam_room_id, exam_code, question_id, selected_answer, is_correct)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    submitted_time = datetime.now()

    for item in graded_answers:
        # Kiểm tra kỹ để tránh dict kiểu TF lọt vào
        if isinstance(item['answer'], dict):
            continue  # Bỏ qua TF, đã xử lý riêng
        try:
            cursor.execute(insert_query, (
                int(student_id),
                int(room_code),
                str(exam_code),
                int(item['question_id']),
                str(item['answer']),
                bool(item['is_correct']),
                submitted_time
            ))
        except Exception as e:
            print(f"Lỗi khi lưu item: {item} → {e}")

    conn.commit()
    cursor.close()
    conn.close()

def save_sa_submission(student_exam_id, sa_submissions):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 🔍 Truy ngược thông tin sinh viên, phòng thi, mã đề
    cursor.execute("""
        SELECT s.id AS student_id, r.id AS exam_room_id, e.exam_code
        FROM student_exams e
        JOIN students s ON e.student_code = s.student_id
        JOIN exam_rooms r ON r.room_code = e.room_code
        WHERE e.id = %s
    """, (student_exam_id,))
    
    result = cursor.fetchone()
    if not result:
        cursor.close()
        conn.close()
        raise ValueError("❌ Không tìm thấy thông tin phiên làm bài.")
    
    student_id = result['student_id']
    exam_room_id = result['exam_room_id']
    exam_code = result['exam_code']
    submitted_at = datetime.now()

    # 📥 Thực hiện lưu từng câu tự luận
    insert_query = """
        INSERT INTO student_sa_submissions
        (student_id, exam_room_id, exam_code, question_id, answer_text, is_correct, submitted_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    for item in sa_submissions:
        try:
            cursor.execute(insert_query, (
                student_id,
                exam_room_id,
                exam_code,
                int(item['question_id']),
                str(item['answer']),
                bool(item['is_correct']),
                submitted_at
            ))
        except Exception as e:
            print(f"❌ Lỗi khi lưu item: {item} → {e}")

    conn.commit()
    cursor.close()
    conn.close()

    
# kết thúc hàm cập nhật bài thi của sinh viên

# đây là hàm mới thêm vào kiểm tra sinh viên có bị kick hay khoong

def get_student_status(room_code, student_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT status FROM control_students
        WHERE room_code = %s AND student_code = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (room_code, student_code))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result['status'] if result else None


# đây là hàm mới thêm vào
def set_student_status(room_code, student_code, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO control_students (room_code, student_code, status)
        VALUES (%s, %s, %s)
    """, (room_code, student_code, status))
    conn.commit()
    cursor.close()
    conn.close()

# kêt thúc hàm mới thêm vào
def get_pending_students(room_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT student_code FROM control_students
        WHERE room_code = %s AND status = 'pending'
        ORDER BY created_at DESC
    """, (room_code,))
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return students

# lllllll

def approve_student(room_code, student_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO control_students (room_code, student_code, status)
        VALUES (%s, %s, 'allowed')
    """, (room_code, student_code))
    conn.commit()
    cursor.close()
    conn.close()

# reject

def reject_student(room_code, student_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO control_students (room_code, student_code, status)
        VALUES (%s, %s, 'blocked')
    """, (room_code, student_code))
    conn.commit()
    cursor.close()
    conn.close()
    

# kết thúc hàm kiểm tra trạng thái sinh viên
def insert_mcq_question(question_data):
    """
    Chèn một câu hỏi MCQ mới vào bảng 'questions'.

    Args:
        question_data (dict): Dictionary chứa dữ liệu câu hỏi.
                              Phải có: 'exam_set_id', 'user_id', 'question_text',
                              'answer_a', 'answer_b', 'answer_c', 'answer_d',
                              'correct_answer'.
                              Có thể có: 'chapter' và 'difficulty' (sẽ là None nếu không có hoặc rỗng).

    Returns:
        int | None: ID của câu hỏi vừa được chèn nếu thành công, hoặc None nếu có lỗi.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO questions (
            exam_set_id, user_id, question_text,
            answer_a, answer_b, answer_c, answer_d,
            correct_answer, chapter, difficulty
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    # Lấy và chuẩn bị giá trị cho chapter và difficulty
    # Đảm bảo chúng là int hoặc None (cho NULL trong DB)
    chapter_val = question_data.get('chapter')
    difficulty_val = question_data.get('difficulty')

    try:
        # Chuyển đổi sang int hoặc giữ None
        # Nếu giá trị là chuỗi rỗng '' hoặc None, nó sẽ trở thành None.
        # Nếu giá trị không thể chuyển đổi thành int (ví dụ: 'abc'), nó sẽ gây ra ValueError.
        final_chapter = int(chapter_val) if chapter_val is not None and str(chapter_val).strip() != '' else None
        final_difficulty = int(difficulty_val) if difficulty_val is not None and str(difficulty_val).strip() != '' else None
    except ValueError:
        # Ném lại ValueError để hàm gọi (import_questions_from_xlsx) có thể bắt và thông báo lỗi cụ thể
        raise ValueError(f"Giá trị Chapter ('{chapter_val}') hoặc Difficulty ('{difficulty_val}') không hợp lệ (không phải số nguyên).")

    values = (
        question_data['exam_set_id'],
        question_data['user_id'],
        question_data['question_text'],
        question_data['answer_a'],
        question_data['answer_b'],
        question_data['answer_c'],
        question_data['answer_d'],
        question_data['correct_answer'],
        final_chapter,
        final_difficulty
    )

    try:
        cursor.execute(query, values)
        conn.commit()  # Commit sau khi chèn thành công
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()  # Rollback nếu có lỗi xảy ra
        print(f"Lỗi khi chèn câu hỏi vào CSDL: {e}") # Log lỗi để tiện debug
        return None
    finally:
        cursor.close()
        conn.close()
        
# ĐÂY LÀ NHỮNG HÀM MỚI THÊM VÀO 14/06/2025


def is_full_thpt2025_exam_set(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Cần kiểm tra cả hai bảng đều có dữ liệu
    tf_query = "SELECT 1 FROM tf_questions WHERE exam_set_id = %s LIMIT 1"
    sa_query = "SELECT 1 FROM short_answer_questions WHERE exam_set_id = %s LIMIT 1"

    cursor.execute(tf_query, (exam_set_id,))
    has_tf = cursor.fetchone() is not None

    cursor.execute(sa_query, (exam_set_id,))
    has_sa = cursor.fetchone() is not None

    cursor.close()
    conn.close()

    return has_tf and has_sa

def is_advanced_mcq_exam_set(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT COUNT(*) FROM questions
        WHERE exam_set_id = %s AND (difficulty IS NOT NULL OR chapter IS NOT NULL)
    """
    
    cursor.execute(query, (exam_set_id,))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return result[0] > 0


def get_mcq_original_questions_by_exam_set(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if is_advanced_mcq_exam_set(exam_set_id):
        # MCQ nâng cao: cần nhiều trường hơn
        query = """
            SELECT id, question_text, difficulty, chapter,
                   answer_a, answer_b, answer_c, answer_d, correct_answer
            FROM questions
            WHERE exam_set_id = %s
            ORDER BY id
        """
    else:
        # MCQ thuần: chỉ cần một số trường
        query = """
            SELECT id, question_text, difficulty
            FROM questions
            WHERE exam_set_id = %s
            ORDER BY id
        """

    cursor.execute(query, (exam_set_id,))
    questions = cursor.fetchall()

    cursor.close()
    conn.close()
    return questions




# KẾT THÚC HÀM MỚI THÊM VÀO 14/06/2025










