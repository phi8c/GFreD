import os
import uuid
from flask import Blueprint, request, jsonify, current_app, render_template, redirect, url_for, abort
from werkzeug.utils import secure_filename

from extract_text import extract_chapters_from_pdf, extract_chapters_from_docx, extract_chapters_from_file, extract_chapters_from_pdffs
from generates_questions import generate_mcq_questions, generate_true_false_questions, generate_short_answer_questions, generate_tf_with_images

from models.exam_model import save_mcq_questions, save_tf_questions, save_short_answer_questions, sel_exam_code_id_by_code, save_student_submissions, save_student_tf_submissions, save_mcq_sa_submissions_v2, save_sa_submission, get_room_id_by_code

from models.exam_model import get_exam_questions_by_code, save_student_submission, get_correct_answer, save_student_exam, save_student_answer, update_student_exam_score, get_exam_code_id_by_code, is_advanced_exam_set, sel_exam_code_id_by_code

from flask_login import current_user, login_required

from datetime import datetime, timedelta
import random
from gen_questions import get_db_connection

from gen_questions import create_exam_set
from collections import defaultdict
import collections
from controllers.extensions import socketio

exam_hs_bp = Blueprint('exam_hs', __name__)

@exam_hs_bp.route('/thpt2025/exam/<int:student_exam_id>', methods=['GET'])
def thpt2025_exam(student_exam_id):
    
    
    student_code = request.args.get('student_code')
    
    
    room_code = request.args.get('room_code')
    
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT submitted FROM student_exams
        WHERE room_code = %s AND student_code = %s
    """, (room_code, student_code))
    record = cursor.fetchone()

    if record:
      if record['submitted']:
        return "bạn đã nộp bài!!!"
    
    

    # 1. Truy vấn thông tin student_exam để lấy exam_code
    cursor.execute("""
        SELECT se.id, se.student_code, se.student_name, se.exam_code, se.room_code, r.duration_minutes
        FROM student_exams se
        JOIN exam_rooms r ON r.room_code = se.room_code
        WHERE se.id = %s
    """, (student_exam_id,))
    student_info = cursor.fetchone()

    if not student_info:
        cursor.close()
        conn.close()
        return abort(404, "Không tìm thấy thông tin sinh viên hoặc mã đề.")
    
    
    student_code = student_info['student_code']
    room_codess = student_info['room_code']


    exam_code = student_info['exam_code']
    print("in ra ra exam_code", exam_code)
    
    exam_code_id = sel_exam_code_id_by_code(exam_code)

    # 2. Truy vấn câu hỏi từ 3 loại bảng theo mã đề
    cursor.execute("""
        SELECT m.id AS map_id, q.id AS question_id, q.question_text,
               m.answer_a, m.answer_b, m.answer_c, m.answer_d
        FROM exam_question_map m
        JOIN questions q ON q.id = m.question_id
        WHERE m.exam_code_id = %s 
        ORDER BY m.question_order ASC
    """, (exam_code_id,))
    mcq_questions = cursor.fetchall()
    #print("int ra câu hỏi trắc nghiệm", mcq_questions)
    
    # 1. Truy vấn câu hỏi đúng sai
    cursor.execute("""
    SELECT m.id AS map_id, q.id AS question_id, q.question_text, q.image_url
    FROM hs_question_map m
    JOIN tf_questions q ON q.id = m.original_question_id
    WHERE m.exam_code_id = %s AND m.question_type = 'tf'
    ORDER BY m.position ASC
""", (exam_code_id,))
    tf_questions = cursor.fetchall()
    print("in ra tf_question", tf_questions)

# 2. Với mỗi câu hỏi đúng sai, truy vấn mệnh đề
    for tf in tf_questions:
        cursor.execute("""
        SELECT id, label, content, is_true, position
        FROM hs_tf_statements
        WHERE hs_map_id = %s
        ORDER BY position
    """, (tf['map_id'],))
        tf['statements'] = cursor.fetchall()
        
        dkl = tf['statements']
        
        print("in ra tf_question", dkl)


    # cursor.execute("""
    #     SELECT m.id AS map_id, q.id AS question_id, q.question_text, q.image_url,
    #            s.content
    #     FROM hs_question_map m
    #     JOIN tf_questions q ON q.id = m.question_id
    #     JOIN hs_tf_statements s ON s.question_map_id = m.id
    #     WHERE m.exam_code_id = %s AND m.question_type = 'tf'
    #     ORDER BY m.question_order ASC
    # """, (exam_code,))
    # tf_questions = cursor.fetchall()

    cursor.execute("""
        SELECT m.id AS map_id, q.id AS question_id, q.question_text
        FROM hs_question_map m
        JOIN short_answer_questions q ON q.id = m.original_question_id
        WHERE m.exam_code_id = %s AND  m.question_type = " "
        ORDER BY m.position ASC
    """, (exam_code_id,))
    sa_questions = cursor.fetchall()
    print("in ra câu hỏi trả lời ngắn", sa_questions)
    
    
    print("in ra mã phòng ở route thi", room_code)
    
    cursor.execute("SELECT duration_minutes FROM exam_rooms WHERE room_code = %s", (room_codess,))
    exam_room = cursor.fetchone()
    duration = exam_room['duration_minutes']

# End time = từ lúc sinh viên vào bắt đầu tính
    #end_time = datetime.now() + timedelta(minutes=duration)
    cursor.execute("""
    SELECT se.start_time, er.duration_minutes
    FROM student_exams se
    JOIN exam_rooms er ON se.room_code = er.room_code
    WHERE se.room_code = %s AND se.student_code = %s
    """, (room_codess, student_code))
    result = cursor.fetchone()
    
    
    if result:
        start_time = result['start_time']
        duration = result['duration_minutes']  # Lấy đúng duration

    # ✅ Sau khi đã đọc xong, có thể đóng
        cursor.fetchall()  # Đọc nốt các dòng còn lại nếu có, tránh lỗi
        cursor.close()
        conn.close()

        end_time = start_time + timedelta(minutes=duration)
        end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
    else:
        cursor.close()
        conn.close()
        raise ValueError("Không tìm thấy dữ liệu thời gian phòng thi.")
    
    # start_time = result['start_time']


    # cursor.close()
    # conn.close()
    
    # end_time = start_time + timedelta(minutes=duration)
    # end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
    # start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
    
    
    

    return render_template("student_thpt_exam.html",
                           student_name=student_info['student_name'],
                           student_code=student_info['student_code'],
                           exam_code=exam_code,
                           room_code=student_info['room_code'],
                           end_time=end_time_str,
                           mcq_questions=mcq_questions,
                           tf_questions=tf_questions,
                           sa_questions=sa_questions,
                           student_exam_id=student_exam_id)

# ROUTE NÀY ĐỂ CHẤM ĐIỂM


@exam_hs_bp.route('/submit_thpt2025_exam', methods=['POST'])
def submit_thpt2025_exam():
    student_exam_id = request.form.get('student_exam_id')
    room_code = request.form.get('room_code')
    
    # student_code = request.form.get('student_code')
    
    
    # Kết nối DB nếu chưa
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

# ✅ Lấy student_code từ bảng student_exams theo ID
    cursor.execute("""
        SELECT student_code FROM student_exams
        WHERE id = %s
    """, (student_exam_id,))
    result = cursor.fetchone()

    if result:
        student_code = result['student_code']
        print("✅ Đã truy xuất student_code từ DB:", student_code)
    else:
        print("❌ Không tìm thấy student_code với ID:", student_exam_id)

    

    # 1. Thu thập câu trả lời từ form
    mcq_answers = {}
    tf_answers = {}
    sa_answers = {}

    for key in request.form:
        if key.startswith('mcq_'):
            question_id = key.replace('mcq_', '')
            mcq_answers[question_id] = request.form.get(key)
            
        elif key.startswith('tf_'):
            stmt_id = key.replace('tf_', '')
            tf_answers[stmt_id] = request.form.get(key) == 'true'

        # elif key.startswith('tf_'):  # tf_123_a (question_map_id + _ + statement key)
        #     parts = key.split('_')  # ['tf', '123', 'a']
        #     if len(parts) == 3:
        #         qid = parts[1]
        #         stmt = parts[2]
        #         if qid not in tf_answers:
        #             tf_answers[qid] = {}
        #         tf_answers[qid][stmt] = request.form.get(key) == 'true'

        elif key.startswith('sa_'):
            question_id = key.replace('sa_', '')
            sa_answers[question_id] = request.form.get(key)
            print(f"[Form Key] {key} = {request.form.get(key)}")
            
    
    
    

    

    # 2. Tính điểm
    score = grade_thpt2025_exam(
        student_exam_id=student_exam_id,
        room_code=room_code,
        mcq_answers=mcq_answers,
        tf_answers=tf_answers,
        sa_answers=sa_answers
    )
    
    # cập nhật điểm sinh viên và trạng thái vào bảng csdl
    
    #update_student_exam_score(student_code, room_code, score)
    
    # kết thúc cập nhật

    # 3. Hiển thị kết quả
    
    print("in ra student_code", student_code)
    
    socketio.emit('student_submitted', {
        'student_code': student_code,
        'room_code': room_code,
        'score': score
    }, namespace='/webrtc')
    
    print(f"✅ Bài thi đã được nộp! Điểm số của bạn: {score}/10", "success")
    #return redirect(url_for('exam_hs.result_hs', student_exam_id=student_exam_id))
    return render_template('result_hs.html', score=score)


# KẾT THÚC ROUTE CHẤM ĐIỂM

def grade_thpt2025_exam(student_exam_id, room_code, mcq_answers, tf_answers, sa_answers):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ==== 1. Lấy đáp án đúng từ DB ====
    
    
    # 1.1 MCQ
    # Bước 1: Lấy exam_code_id từ student_exams
    cursor.execute("""
    SELECT ec.id AS exam_code_id, se.exam_code as exam_coded
    FROM student_exams se
    JOIN exam_codes ec ON ec.code = se.exam_code
    WHERE se.id = %s
""", (student_exam_id,))
    exam_code_row = cursor.fetchone()

    if not exam_code_row:
        cursor.close()
        conn.close()
        abort(404, "Không tìm thấy mã đề thi.")

    exam_code_id = exam_code_row['exam_code_id']
    exam_code = exam_code_row['exam_coded']
    
    
    cursor.execute("""
    SELECT question_id, correct_answer
    FROM exam_question_map
    WHERE exam_code_id = %s
""", (exam_code_id,))
    correct_mcq_rows = cursor.fetchall()
    correct_mcq = {str(row['question_id']): row['correct_answer'] for row in correct_mcq_rows}
    mcq_total = len(correct_mcq)
    
    print("in ra khi lấy đáp án đúng ở câu mqc", correct_mcq)

    # 1.2 TF
    cursor.execute("""
    SELECT ec.id AS exam_code_id
    FROM student_exams se
    JOIN exam_codes ec ON ec.code = se.exam_code
    WHERE se.id = %s
""", (student_exam_id,))
    exam_code_row = cursor.fetchone()

    if not exam_code_row:
        cursor.close()
        conn.close()
        abort(404, "Không tìm thấy mã đề thi.")

    exam_code_id = exam_code_row['exam_code_id']
    
    cursor.execute("""
    SELECT s.id AS statement_id, s.is_true
    FROM hs_question_map m
    JOIN hs_tf_statements s ON m.id = s.hs_map_id
    WHERE m.exam_code_id = %s AND m.question_type = 'tf'
""", (exam_code_id,))
    tf_data = cursor.fetchall()
    tf_total = len(tf_data)
    print("in ra câu hỏi đúng sai khi lấy đáp án đúng", tf_data)
    
    
    cursor.execute("""
    SELECT ec.id AS exam_code_id
    FROM student_exams se
    JOIN exam_codes ec ON ec.code = se.exam_code
    WHERE se.id = %s
""", (student_exam_id,))
    exam_code_row = cursor.fetchone()

    if not exam_code_row:
        cursor.close()
        conn.close()
        abort(404, "Không tìm thấy mã đề thi.")

    exam_code_id = exam_code_row['exam_code_id']
    
    
    cursor.execute("""
    SELECT m.id AS map_id, q.correct_answer, m.original_question_id AS id_org
    FROM hs_question_map m
    JOIN short_answer_questions q ON m.original_question_id = q.id
    WHERE m.exam_code_id = %s AND  m.question_type = " "
""", (exam_code_id,))
    sa_data = cursor.fetchall()
    sa_total = len(sa_data)
    print("lấy ra đáp án đúng ở dạng trả lời ngắn")

    # ==== 2. Tính điểm từng phần ====

    # 2.1 MCQ
    graded_answers = []  # Lưu từng câu để sau này insert vào student_exam_submissions

    mcq_score = 0
    if mcq_total > 0:
        mcq_point_per_question = 3.0 / mcq_total
        #is_correct = False
        for qid, correct_ans in correct_mcq.items():
            #print(f"[MCQ] QID: {qid}, Student: {student_ans}, Correct: {correct_ans}")
            student_ans = mcq_answers.get(qid)
            print(f"[MCQ] QID: {qid}, Student: {student_ans}, Correct: {correct_ans}")
            is_correct = False
            if student_ans and student_ans.upper() == correct_ans.upper():
                mcq_score += mcq_point_per_question
                is_correct = True
            graded_answers.append({
            'question_id': qid,
            'answer': student_ans,
            'is_correct': is_correct
        })

    # 2.2 TF
    # TF - Đúng / Sai
    tf_test = []
    
    ###########
    
    # Làm phẳng tf_answers: chuyển từ {map_id: {...}} → {statement_id: True/False}
    # flattened_tf_answers = {}

    # for map_val in tf_answers.values():
    #     for statement_id, answer in map_val.items():
    #         flattened_tf_answers[str(statement_id)] = answer

    # tf_answers = flattened_tf_answers

    
    ##########
    
    tf_submissions = []
    
    tf_score = 0
    
    # --- BẮT ĐẦU PHẦN CHỈNH SỬA ---

# Bước 1: Lấy tất cả các mệnh đề Đúng/Sai và nhóm chúng theo map_id
    cursor.execute("""
    SELECT m.id AS map_id, s.id AS statement_id, s.is_true
    FROM hs_question_map m
    JOIN hs_tf_statements s ON m.id = s.hs_map_id
    WHERE m.exam_code_id = %s AND m.question_type = 'tf'
""", (exam_code_id,))
    tf_rows = cursor.fetchall()

    tf_grouped = collections.defaultdict(list)
    for row in tf_rows:
        tf_grouped[row['map_id']].append({
        'statement_id': str(row['statement_id']),
        'is_true': row['is_true']
        })

# Bước 2: Đếm tổng số câu hỏi Đúng/Sai thực tế (tức là số lượng map_id duy nhất)
    tf_total_questions = len(tf_grouped)

# Bước 3: Tính toán trọng số điểm cho mỗi câu hỏi Đúng/Sai
# Tổng điểm phần Đúng/Sai là 4.0. Chia đều cho số câu hỏi thực tế.
    if tf_total_questions > 0:
        tf_point_per_question = 4.0 / tf_total_questions
    else:
        tf_point_per_question = 0.0 # Tránh lỗi chia cho 0 nếu không có câu hỏi nào

# Các phần còn lại không thay đổi, vẫn giữ nguyên logic để đảm bảo đầu ra
    cursor.execute("""
    SELECT s.id as student_id, se.student_code as student_code
    FROM student_exams se
    JOIN students s ON se.student_code = s.student_id
    WHERE se.id = %s
""", (student_exam_id,))

    result = cursor.fetchone()
    print("in ra result", result)
    if not result:
        raise Exception("Không tìm thấy thông tin sinh viên")

    student_id = result['student_id']
    student_code = result['student_code']

# Lặp qua từng câu hỏi (map_id) để tính điểm
    for map_id, statements in tf_grouped.items():
        correct_count = 0
        for stmt in statements:
            sid = stmt['statement_id']
            correct = stmt['is_true']

        # Debug prints (có thể xóa sau khi kiểm thử)
            print("in ra correct", correct)
            print("Các key trong tf_answers:", tf_answers.keys())
            print("in ra tf_answer thuần", tf_answers)

            student_val = tf_answers.get(str(sid))
            print(f"    - Statement ID: {sid}, Student: {student_val}, Correct: {correct}")

        # Quan trọng: Đảm bảo student_val không phải None trước khi so sánh
        # và kiểu dữ liệu phù hợp (nếu student_val là string và correct là boolean, cần chuyển đổi)
        # Giả định student_val đã là boolean hoặc có thể so sánh trực tiếp với correct
            is_correct = (student_val == correct) if student_val is not None else False
            
            exam_room_id = get_room_id_by_code(room_code)
        # print("in ra is correct", is_correct)

            tf_submissions.append({
            'student_id': student_id,
            'exam_room_id': exam_room_id,
            'exam_code': exam_code,
            'map_id': map_id,
            'statement_id': sid,
            'student_answer': student_val,  # Boolean: True/False
            'is_correct': is_correct         # Boolean: True/False
            })

            # tf_test.append({
            # 'statement_id': sid,
            # 'student_answer': student_val,
            # 'is_correct': is_correct
            # })

        # Debug prints (có thể xóa sau khi kiểm thử)
        # print("in ra danh sách chứa tf submissions", tf_submissions)
        # print("in ra danh sách chứa tf test", tf_test)

            if is_correct:
                correct_count += 1

    # Tính điểm cho TỪNG CÂU hỏi dựa trên số mệnh đề đúng và trọng số của câu đó
        point_percentage = 0.0
        if correct_count == 1:
            point_percentage = 0.10 # 10%
        elif correct_count == 2:
            point_percentage = 0.25 # 25%
        elif correct_count == 3:
            point_percentage = 0.50 # 50%
        elif correct_count == 4:
            point_percentage = 1.00 # 100%
    # Nếu correct_count là 0, point_percentage vẫn là 0.0

    # Tính điểm thực tế của câu này
        point_for_this_question = tf_point_per_question * point_percentage
        tf_score += point_for_this_question

# --- KẾT THÚC PHẦN CHỈNH SỬA ---

# print("Tổng điểm phần Đúng/Sai sau khi chấm:", tf_score)
#     if tf_total > 0:
#         tf_weight = 4.0 / 4  # vì bạn nói rõ có 4 câu dạng đúng sai => mỗi câu 1 điểm (tổng điểm phần này là 4)
        
        
#         cursor.execute("""
#     SELECT s.id as student_id
#     FROM student_exams se
#     JOIN students s ON se.student_code = s.student_id  
#     WHERE se.id = %s
# """, (student_exam_id,))

#         result = cursor.fetchone()
#         if not result:
#             raise Exception("Không tìm thấy thông tin sinh viên")

#         student_id = result['student_id']
    
#     # Nhóm các statement theo map_id (1 map_id là 1 câu hỏi đúng/sai gồm 4 mệnh đề)
#         cursor.execute("""
#         SELECT m.id AS map_id, s.id AS statement_id, s.is_true
#         FROM hs_question_map m
#         JOIN hs_tf_statements s ON m.id = s.hs_map_id
#         WHERE m.exam_code_id = %s AND m.question_type = 'tf'
#     """, (exam_code_id,))
#         tf_rows = cursor.fetchall()

#     # Gom các mệnh đề thành từng nhóm theo map_id
    

#         tf_grouped = defaultdict(list)
#         for row in tf_rows:
#             tf_grouped[row['map_id']].append({
#             'statement_id': str(row['statement_id']),
#             'is_true': row['is_true']
#         })

#         for map_id, statements in tf_grouped.items():
#             correct_count = 0
#             for stmt in statements:
#                 sid = stmt['statement_id']
#                 correct = stmt['is_true']
#                 print("in ra correct", correct)
#                 print("Các key trong tf_answers:", tf_answers.keys())

#                 student_val = tf_answers.get(sid)
#                 print(f"   - Statement ID: {sid}, Student: {student_val}, Correct: {correct}")
#                 if student_val is None:
#                     continue
#                 is_correct = (student_val == correct)
#                 print("in ra is correct", is_correct)
#             # THAY:
# # if student_val.lower() == str(correct).lower():
#                 tf_submissions.append({
#                     'student_id': student_id,
#                     'exam_room_id': room_code,
#                     'exam_code': exam_code,
#                     'map_id': map_id,
#                     'statement_id': sid,
#                     'student_answer': student_val,  # Boolean: True/False
#                     'is_correct': is_correct          # Boolean: True/False
#                     })
                
#                 tf_test.append({
#                     'statement_id': sid,
#                     'student_answer': student_val,
#                     'is_correct': is_correct
#                     })
                
#                 print("in ra danh sách chứa tf submissions", tf_submissions)
#                 print("in ra danh sách chứa tf test", tf_test)

# # BẰNG:
#                 if is_correct:

#                     correct_count += 1
                
            
                    
                
                
       

#         # Tính điểm theo số mệnh đề đúng
#         if correct_count == 1: 
#             point = 0.1
#         elif correct_count == 2:
#             point = 0.25
#         elif correct_count == 3:
#             point = 0.5
#         elif correct_count == 4:
#             point = 1.0
#         else:
#             point = 0.0

#         tf_score += point  # vì mỗi câu đã scale sẵn là max 1.0


    # 2.3 SA
    sa_submissions = []
    sa_score = 0
    if sa_total > 0:
        sa_point_per_question = 3.0 / sa_total
        for item in sa_data:
            map_id = str(item['id_org'])
            #qid = str(item['question_id'])
            correct_ans = item['correct_answer'].strip().lower()
            #student_ans = sa_answers.get(map_id, '').strip().lower()
            student_ans = str(sa_answers.get(map_id, '')).strip().lower()
            print(f"[SA] QID: {map_id}, Student: {student_ans}, Correct: {correct_ans}")
            is_correct = (student_ans == correct_ans)
            if is_correct:
                sa_score += sa_point_per_question
            sa_submissions.append({
            'question_id': map_id,
            'answer': student_ans,
            'is_correct': is_correct
     })

    # ==== 3. Tổng điểm (làm tròn 2 chữ số thập phân) ====
    #print("in ra gộp đáp án ", graded_answers)
    total_score = round(mcq_score + tf_score + sa_score, 2)
    
    print("in ra ĐIỂM", total_score)
    
    
    #return "chấm điểm xong"
    
    
    
    
    save_student_tf_submissions(tf_submissions)

    # ==== 4. Cập nhật kết quả ====
    update_student_exam_score(student_code, room_code, total_score)
    
    print("in ra danh sách chứa tf submissions ở đây đã là ngoài vòng lặp", tf_submissions)
    
    save_student_tf_submissions(tf_submissions)
    
    #save_student_submissions(student_exam_id, room_code, exam_code_row, graded_answers)
    save_mcq_sa_submissions_v2(student_exam_id, graded_answers)
    
    save_sa_submission(student_exam_id, sa_submissions)


    cursor.close()
    conn.close()

    return total_score






