from flask import Blueprint, render_template, request, redirect, url_for
from models.exam_model import create_exam_room, assign_exam_code, get_exam_sets, get_room_id_by_code
import random
from gen_questions import get_db_connection
from utils.export_exam_utils import export_exam_package, generate_score_excel, export_student_exam_to_docx
from flask import send_file
from datetime import datetime, timedelta
from controllers.extensions import socketio
from flask import jsonify
import openpyxl
from controllers.mail_event import send_otp_email
from flask_login import current_user, login_required


import io
import zipfile




#room_bp = Blueprint('room_bp', __name__)

statistical_bp = Blueprint('statistical', __name__)


@statistical_bp.route('/statistical-room', methods=['GET'])
def show_exam_rooms():
    search = request.args.get('search', '')
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    
    user_id = current_user.id  # Lấy user_id từ current_user

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT id, room_code, subject_name, created_at
        FROM exam_rooms
        WHERE created_by_user_id = %s  # Điều kiện theo user_id
    """
    params = [user_id]  # Chỉ lấy các phòng thi của user hiện tại

    if search:
        query += " AND (room_code LIKE %s OR subject_name LIKE %s)"
        search_pattern = f"%{search}%"
        params += [search_pattern, search_pattern]

    if from_date:
        query += " AND created_at >= %s"
        params.append(from_date)

    if to_date:
        query += " AND created_at <= %s"
        params.append(to_date)

    query += " ORDER BY created_at DESC"

    cursor.execute(query, params)
    exam_rooms = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('room_management.html', exam_rooms=exam_rooms)
@statistical_bp.route('/statistical-room/<int:room_id>', methods=['GET'])
@login_required
def show_students_in_room(room_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy thông tin chi tiết phòng thi
    cursor.execute("""
        SELECT room_code, subject_name, duration_minutes, created_at, open_time, grading_mode
        FROM exam_rooms
        WHERE id = %s AND created_by_user_id = %s
    """, (room_id, current_user.id))
    room_info = cursor.fetchone()

    if not room_info:
        cursor.close()
        conn.close()
        return "Phòng thi không tồn tại hoặc không thuộc quyền truy cập.", 404

    # Lấy danh sách sinh viên thi trong phòng đó
    cursor.execute("""
        SELECT id, student_name, student_code
        FROM student_exams
        WHERE room_code = %s
        ORDER BY student_name
    """, (room_info['room_code'],))
    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('student_list.html', room_info=room_info, students=students)

# route này mới thêm vào

@statistical_bp.route('/student-exam/<int:student_exam_id>', methods=['GET'])
def view_student_exam(student_exam_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    
    
    # --- Lấy thông tin bài thi của sinh viên ---
    cursor.execute("""
        SELECT se.id, se.student_name, se.student_code, se.room_code, se.exam_code,
               se.start_time, se.end_time, se.score, se.status,
               er.subject_name, er.duration_minutes, er.open_time,
               ec.id AS exam_code_id, ec.exam_set_id
        FROM student_exams se
        JOIN exam_rooms er ON se.room_code = er.room_code
        JOIN exam_codes ec ON se.exam_code = ec.code
        WHERE se.id = %s
    """, (student_exam_id,))
    exam_info = cursor.fetchone()

    if not exam_info:
        cursor.close()
        conn.close()
        return "Không tìm thấy bài thi", 404

    exam_code_id = exam_info['exam_code_id']
    exam_set_id = exam_info['exam_set_id']
    exam_code = exam_info['exam_code']

    # --- Kiểm tra xem có phải đề THPT 2025 không ---
    cursor.execute("SELECT COUNT(*) AS tf_count FROM tf_questions WHERE exam_set_id = %s", (exam_set_id,))
    tf_count = cursor.fetchone()['tf_count']

    cursor.execute("SELECT COUNT(*) AS sa_count FROM short_answer_questions WHERE exam_set_id = %s", (exam_set_id,))
    sa_count = cursor.fetchone()['sa_count']

    is_thpt2025 = tf_count > 0 or sa_count > 0

    all_questions = []

    if not is_thpt2025:
        # ==== Đề thuần MCQ ====
        cursor.execute("""
            SELECT sqm.question_id, sqm.question_order, sqm.answer_a, sqm.answer_b,
                   sqm.answer_c, sqm.answer_d, sqm.correct_answer,
                   q.question_text AS question_content
            FROM exam_question_map sqm
            JOIN questions q ON sqm.question_id = q.id
            WHERE sqm.exam_code_id = %s
            ORDER BY sqm.question_order
        """, (exam_code_id,))
        mcq_questions = cursor.fetchall()

        cursor.execute("""
            SELECT question_id, selected_answer, is_correct
            FROM student_exam_submissions
            WHERE student_id = %s AND exam_code = %s
        """, (student_exam_id, exam_code))
        submissions = {s['question_id']: s for s in cursor.fetchall()}

        for q in mcq_questions:
            sub = submissions.get(q['question_id'], {})
            all_questions.append({
                'type': 'MCQ',
                'question_text': q['question_content'],
                'selected_answer': sub.get('selected_answer'),
                'correct_answer': q['correct_answer'],
                'is_correct': sub.get('is_correct'),
                'options': [
                    {'label': 'A', 'text': q['answer_a']},
                    {'label': 'B', 'text': q['answer_b']},
                    {'label': 'C', 'text': q['answer_c']},
                    {'label': 'D', 'text': q['answer_d']},
                ]
            })

    else:
        # ==== Đề THPT 2025 (MCQ + TF + SA) ====

        # MCQ
        cursor.execute("""
            SELECT sqm.question_id, sqm.answer_a, sqm.answer_b, sqm.answer_c, sqm.answer_d,
                   sqm.correct_answer, q.question_text
            FROM exam_question_map sqm
            JOIN questions q ON q.id = sqm.question_id
            WHERE sqm.exam_code_id = %s
        """, (exam_code_id,))
        mcqs = cursor.fetchall()
        cursor.execute("SELECT * FROM student_exam_submissions WHERE student_id = %s AND exam_code = %s",
                       (student_exam_id, exam_code))
        mcq_subs = {s['question_id']: s for s in cursor.fetchall()}

        for q in mcqs:
            sub = mcq_subs.get(q['question_id'], {})
            all_questions.append({
                'type': 'MCQ',
                'question_text': q['question_text'],
                'selected_answer': sub.get('selected_answer'),
                'correct_answer': q['correct_answer'],
                'is_correct': sub.get('is_correct'),
                'options': [
                    {'label': 'A', 'text': q['answer_a']},
                    {'label': 'B', 'text': q['answer_b']},
                    {'label': 'C', 'text': q['answer_c']},
                    {'label': 'D', 'text': q['answer_d']},
                ]
            })

        # TF
        cursor.execute("""
            SELECT hqm.id AS hs_map_id, hqm.original_question_id, hqm.position, tf.question_text
            FROM hs_question_map hqm
            JOIN tf_questions tf ON tf.id = hqm.original_question_id
            WHERE hqm.exam_code_id = %s AND hqm.question_type = 'tf'
            ORDER BY hqm.position
        """, (exam_code_id,))
        tf_items = cursor.fetchall()

        cursor.execute("SELECT * FROM student_tf_submissions WHERE student_id = %s AND exam_code = %s",
                       (student_exam_id, exam_code))
        tf_subs = cursor.fetchall()
        tf_map = {(s['hs_map_id'], s['label']): s for s in tf_subs}

        for tf in tf_items:
            cursor.execute("""
                SELECT label, content, is_true
                FROM hs_tf_statements
                WHERE hs_map_id = %s
                ORDER BY position
            """, (tf['hs_map_id'],))
            statements = cursor.fetchall()

            # Gắn kèm đáp án của SV vào từng statement
            for st in statements:
                s_key = (tf['hs_map_id'], st['label'])
                s_sub = tf_map.get(s_key, {})
                st['student_answer'] = s_sub.get('is_true')
                st['is_correct'] = s_sub.get('is_correct')

            all_questions.append({
                'type': 'TF',
                'question_text': tf['question_text'],
                'statements': statements
            })

        # SA
        cursor.execute("""
            SELECT hqm.original_question_id, hqm.position, sa.question_text
            FROM hs_question_map hqm
            JOIN short_answer_questions sa ON sa.id = hqm.original_question_id
            WHERE hqm.exam_code_id = %s AND (hqm.question_type IS NULL OR hqm.question_type = '')
            ORDER BY hqm.position
        """, (exam_code_id,))
        sa_items = cursor.fetchall()

        cursor.execute("SELECT * FROM student_sa_submissions WHERE student_id = %s AND exam_code = %s",
                       (student_exam_id, exam_code))
        sa_subs = {s['question_id']: s for s in cursor.fetchall()}

        for sa in sa_items:
            sub = sa_subs.get(sa['original_question_id'], {})
            all_questions.append({
                'type': 'SA',
                'question_text': sa['question_text'],
                'student_answer': sub.get('answer_text'),
                'is_correct': sub.get('is_correct')
            })

    cursor.close()
    conn.close()

    return render_template(
        'student_exam_detail.html',
        student_exam=exam_info,
        questions=all_questions,
        is_thpt2025=is_thpt2025
    )
@statistical_bp.route('/export_score/<room_code>')
def export_room_score_excel(room_code):
    room_info, score_data = fetch_exam_room_and_scores(room_code)
    return generate_score_excel(room_code, room_info, score_data)


def fetch_exam_room_and_scores(room_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Lấy thông tin phòng thi
    cursor.execute("""
        SELECT er.room_code, er.subject_name, er.open_time, er.duration_minutes,
               er.created_at, u.username AS instructor_name
        FROM exam_rooms er
        LEFT JOIN users u ON u.id = er.created_by_user_id
        WHERE er.room_code = %s
    """, (room_code,))
    room_info = cursor.fetchone()

    # 2. Lấy điểm sinh viên
    cursor.execute("""
        SELECT se.student_code, se.student_name, se.exam_code, se.score,
               se.start_time, se.end_time, se.status, rs.full_name
        FROM student_exams se
        LEFT JOIN exam_rooms er ON se.room_code = er.room_code
        LEFT JOIN room_students rs ON rs.student_id = se.student_code AND rs.room_id = er.id
        WHERE se.room_code = %s
        ORDER BY se.start_time
    """, (room_code,))
    scores = cursor.fetchall()

    cursor.close()
    conn.close()
    return room_info, scores

# đoạn này mới thêm vào để biểu diễn quá trình tiến bộ


@statistical_bp.route('/progress')
@login_required
def progress_overview():
    return render_template('progress.html')


@statistical_bp.route('/classes', methods=['GET'])
@login_required
def list_classes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT DISTINCT class_name
            FROM students
            ORDER BY class_name
        """)
        classes = cursor.fetchall()

        return jsonify({"success": True, "classes": classes})

    except Exception as e:
        print("❌ Lỗi lấy danh sách lớp:", e)
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()
@statistical_bp.route('/students-in-class/<class_name>', methods=['GET'])
@login_required
def get_students_by_class(class_name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT student_id, full_name
            FROM students
            WHERE class_name = %s
            ORDER BY full_name
        """, (class_name,))
        students = cursor.fetchall()

        return jsonify({"success": True, "students": students})

    except Exception as e:
        print("❌ Lỗi lấy sinh viên trong lớp:", e)
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()
@statistical_bp.route('/progress/student/<student_id>', methods=['GET'])
@login_required
def get_student_progress(student_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT er.created_at AS exam_time, se.score, er.subject_name, er.room_code
            FROM student_exams se
            JOIN exam_rooms er ON se.room_code = er.room_code
            WHERE se.student_code = %s AND se.submitted = 1  AND se.score IS NOT NULL
            ORDER BY er.created_at
        """, (student_id,))
        progress = cursor.fetchall()

        return jsonify({"success": True, "progress": progress})

    except Exception as e:
        print("❌ Lỗi lấy tiến độ sinh viên:", e)
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()
@statistical_bp.route('/progress/class/<class_name>', methods=['GET'])
@login_required
def get_class_progress(class_name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT er.created_at AS exam_time,
                   AVG(se.score) AS avg_score,
                   er.room_code,
                   er.subject_name
            FROM student_exams se
            JOIN students s ON s.student_id = se.student_code
            JOIN exam_rooms er ON se.room_code = er.room_code
            WHERE s.class_name = %s AND se.submitted = 1 AND se.score IS NOT NULL
            GROUP BY er.room_code, er.created_at
            ORDER BY er.created_at
        """, (class_name,))
        progress = cursor.fetchall()

        return jsonify({"success": True, "progress": progress})

    except Exception as e:
        print("❌ Lỗi lấy tiến độ lớp:", e)
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()
        
        
        
@statistical_bp.route('/delete-room/<room_code>', methods=['POST'])
def delete_exam_room(room_code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Lấy room_id từ exam_rooms
        cursor.execute("SELECT id FROM exam_rooms WHERE room_code = %s", (room_code,))
        room_row = cursor.fetchone()
        if not room_row:
            return jsonify({"status": "error", "message": "Không tìm thấy phòng thi."}), 404

        room_id = room_row["id"]

        # 2. Lấy danh sách exam_room_id từ student_exams
        cursor.execute("SELECT id FROM student_exams WHERE room_code = %s", (room_code,))
        student_exams = cursor.fetchall()
        exam_room_ids = [row["id"] for row in student_exams]

        # 3. Xóa dữ liệu liên quan
        if exam_room_ids:
            format_strings = ','.join(['%s'] * len(exam_room_ids))

            cursor.execute(f"DELETE FROM student_tf_submissions WHERE exam_room_id IN ({format_strings})", exam_room_ids)
            cursor.execute(f"DELETE FROM student_sa_submissions WHERE exam_room_id IN ({format_strings})", exam_room_ids)
            cursor.execute(f"DELETE FROM student_exam_submissions WHERE exam_room_id IN ({format_strings})", exam_room_ids)
            cursor.execute(f"DELETE FROM student_exams WHERE id IN ({format_strings})", exam_room_ids)

        cursor.execute("DELETE FROM control_students WHERE room_code = %s", (room_code,))
        cursor.execute("DELETE FROM room_students WHERE room_id = %s", (room_id,))

        # 4. Xóa phòng thi cuối cùng
        cursor.execute("DELETE FROM exam_rooms WHERE id = %s", (room_id,))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "Đã xóa phòng thi và dữ liệu liên quan."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


        
##### HÀM NÀY MỚI THÊM VÀO ĐỂ XUẤT BÀI LÀM SINH VIÊN




def get_student_exam_data(student_exam_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --- Lấy thông tin bài thi ---
    cursor.execute("""
        SELECT se.id, se.student_name, se.student_code, se.room_code, se.exam_code,
               se.start_time, se.end_time, se.score, se.status,
               er.subject_name, er.duration_minutes, er.open_time,
               ec.id AS exam_code_id, ec.exam_set_id
        FROM student_exams se
        JOIN exam_rooms er ON se.room_code = er.room_code
        JOIN exam_codes ec ON se.exam_code = ec.code
        WHERE se.id = %s
    """, (student_exam_id,))
    exam_info = cursor.fetchone()

    if not exam_info:
        cursor.close()
        conn.close()
        return None, [], False

    exam_code_id = exam_info['exam_code_id']
    exam_set_id = exam_info['exam_set_id']
    exam_code = exam_info['exam_code']

    # --- Kiểm tra có phải đề THPT 2025 không ---
    cursor.execute("SELECT COUNT(*) AS tf_count FROM tf_questions WHERE exam_set_id = %s", (exam_set_id,))
    tf_count = cursor.fetchone()['tf_count']

    cursor.execute("SELECT COUNT(*) AS sa_count FROM short_answer_questions WHERE exam_set_id = %s", (exam_set_id,))
    sa_count = cursor.fetchone()['sa_count']

    is_thpt2025 = tf_count > 0 or sa_count > 0
    all_questions = []

    if not is_thpt2025:
        # ==== Đề MCQ thuần ====
        cursor.execute("""
            SELECT sqm.question_id, sqm.question_order, sqm.answer_a, sqm.answer_b,
                   sqm.answer_c, sqm.answer_d, sqm.correct_answer,
                   q.question_text AS question_content
            FROM exam_question_map sqm
            JOIN questions q ON sqm.question_id = q.id
            WHERE sqm.exam_code_id = %s
            ORDER BY sqm.question_order
        """, (exam_code_id,))
        mcq_questions = cursor.fetchall()

        cursor.execute("""
            SELECT question_id, selected_answer, is_correct
            FROM student_exam_submissions
            WHERE student_id = %s AND exam_code = %s
        """, (student_exam_id, exam_code))
        submissions = {s['question_id']: s for s in cursor.fetchall()}

        for q in mcq_questions:
            sub = submissions.get(q['question_id'], {})
            all_questions.append({
                'type': 'MCQ',
                'question_text': q['question_content'],
                'selected_answer': sub.get('selected_answer'),
                'correct_answer': q['correct_answer'],
                'is_correct': sub.get('is_correct'),
                'options': [
                    {'label': 'A', 'text': q['answer_a']},
                    {'label': 'B', 'text': q['answer_b']},
                    {'label': 'C', 'text': q['answer_c']},
                    {'label': 'D', 'text': q['answer_d']},
                ]
            })
    else:
        # ==== Đề THPT 2025 (MCQ + TF + SA) ====

        # MCQ
        cursor.execute("""
            SELECT sqm.question_id, sqm.answer_a, sqm.answer_b, sqm.answer_c, sqm.answer_d,
                   sqm.correct_answer, q.question_text
            FROM exam_question_map sqm
            JOIN questions q ON q.id = sqm.question_id
            WHERE sqm.exam_code_id = %s
        """, (exam_code_id,))
        mcqs = cursor.fetchall()
        cursor.execute("SELECT * FROM student_exam_submissions WHERE student_id = %s AND exam_code = %s",
                       (student_exam_id, exam_code))
        mcq_subs = {s['question_id']: s for s in cursor.fetchall()}

        for q in mcqs:
            sub = mcq_subs.get(q['question_id'], {})
            all_questions.append({
                'type': 'MCQ',
                'question_text': q['question_text'],
                'selected_answer': sub.get('selected_answer'),
                'correct_answer': q['correct_answer'],
                'is_correct': sub.get('is_correct'),
                'options': [
                    {'label': 'A', 'text': q['answer_a']},
                    {'label': 'B', 'text': q['answer_b']},
                    {'label': 'C', 'text': q['answer_c']},
                    {'label': 'D', 'text': q['answer_d']},
                ]
            })

        # TF
        cursor.execute("""
            SELECT hqm.id AS hs_map_id, hqm.original_question_id, hqm.position, tf.question_text, tf.image_url
            FROM hs_question_map hqm
            JOIN tf_questions tf ON tf.id = hqm.original_question_id
            WHERE hqm.exam_code_id = %s AND hqm.question_type = 'tf'
            ORDER BY hqm.position
        """, (exam_code_id,))
        tf_items = cursor.fetchall()

        cursor.execute("SELECT * FROM student_tf_submissions WHERE student_id = %s AND exam_code = %s",
                       (student_exam_id, exam_code))
        tf_subs = cursor.fetchall()
        tf_map = {(s['hs_map_id'], s['label']): s for s in tf_subs}

        for tf in tf_items:
            cursor.execute("""
                SELECT label, content, is_true
                FROM hs_tf_statements
                WHERE hs_map_id = %s
                ORDER BY position
            """, (tf['hs_map_id'],))
            statements = cursor.fetchall()

            for st in statements:
                s_key = (tf['hs_map_id'], st['label'])
                s_sub = tf_map.get(s_key, {})
                st['student_answer'] = s_sub.get('is_true')
                st['is_correct'] = s_sub.get('is_correct')

            all_questions.append({
                'type': 'TF',
                'question_text': tf['question_text'],
                'image_url': tf['image_url'],
                'statements': statements
            })

        # SA
        cursor.execute("""
            SELECT hqm.original_question_id, hqm.position, sa.question_text
            FROM hs_question_map hqm
            JOIN short_answer_questions sa ON sa.id = hqm.original_question_id
            WHERE hqm.exam_code_id = %s AND (hqm.question_type IS NULL OR hqm.question_type = '')
            ORDER BY hqm.position
        """, (exam_code_id,))
        sa_items = cursor.fetchall()

        cursor.execute("SELECT * FROM student_sa_submissions WHERE student_id = %s AND exam_code = %s",
                       (student_exam_id, exam_code))
        sa_subs = {s['question_id']: s for s in cursor.fetchall()}

        for sa in sa_items:
            sub = sa_subs.get(sa['original_question_id'], {})
            all_questions.append({
                'type': 'SA',
                'question_text': sa['question_text'],
                'student_answer': sub.get('answer_text'),
                'is_correct': sub.get('is_correct')
            })

    cursor.close()
    conn.close()
    return exam_info, all_questions, is_thpt2025




###### KẾT THÚC XUẤT BÀI LÀM SINH VIÊN

def export_room_student_exams_to_zip(room_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy danh sách các bài thi của phòng này
    cursor.execute("""
        SELECT id FROM student_exams
        WHERE room_code = %s
        ORDER BY id
    """, (room_code,))
    student_exam_ids = [row['id'] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()

    if not student_exam_ids:
        return "Không có bài thi nào trong phòng này", 404

    # Lấy ngày hiện tại
    today = datetime.now()
    date_str = f"{today.day}_{today.month}_{today.year}"
    folder_name = f"Phong_{room_code}_{date_str}"

    # Tạo file zip trong RAM
    zip_stream = io.BytesIO()
    with zipfile.ZipFile(zip_stream, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for exam_id in student_exam_ids:
            # Lấy dữ liệu bài thi
            exam_info, questions, _ = get_student_exam_data(exam_id)
            if not exam_info:
                continue  # Bỏ qua bài lỗi

            # Xuất file DOCX ra RAM
            doc_stream = io.BytesIO()
            doc = export_student_exam_to_docx(exam_info, questions)
            doc.save(doc_stream)
            doc_stream.seek(0)

            # Tạo tên file
            student_code = exam_info['student_code']
            filename = f"{folder_name}/BaiThi_{student_code}_{date_str}.docx"

            # Ghi vào file zip
            zip_file.writestr(filename, doc_stream.read())

    zip_stream.seek(0)
    zip_filename = f"{folder_name}.zip"
    return send_file(zip_stream, download_name=zip_filename, as_attachment=True)

@statistical_bp.route('/export-room/<room_code>')
def export_room(room_code):
    return export_room_student_exams_to_zip(room_code)






# kết thúc đoạn biểu diễn quá trinh tiến bộ




