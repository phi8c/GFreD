from flask import Blueprint, render_template, request, redirect, url_for, make_response, flash
from models.exam_model import get_exam_questions_by_code, save_student_submission, get_correct_answer, save_student_exam, save_student_answer, update_student_exam_score, get_exam_code_id_by_code, is_advanced_exam_set, sel_exam_code_id_by_code, get_exam_questions_by_code_id, get_student_code_by_exam_and_room, get_student_exam_id
from gen_questions import get_db_connection
from app.controllers.extensions import socketio
from datetime import datetime, timedelta

student_bp = Blueprint('student_bp', __name__)

# Route: Giao diện làm bài thi
@student_bp.route('/take-exam/<room_code>', methods=['GET', 'POST'])
def start_exam(room_code):
    student_name = request.args.get('student_name')
    student_code = request.args.get('student_code')
    #room_code = request.args.get('room_code')  (không cần viết chính xác như này)
    exam_code = request.args.get('exam_code')
    print("in ra student code", student_code)
    print("in ra room code", room_code)
    print("in ra exam code trong phòng thi", exam_code)
    
    result_if_submitted = check_submitted_and_redirect(student_code, room_code)
    if result_if_submitted:
        return result_if_submitted

    
    
    socketio.emit('exam_started', {
        'student_code': student_code,
        'student_name': student_name,
        'room_code': room_code
    }, namespace='/room')

    #student_exam_id = save_student_exam(student_name, student_code, room_code, exam_code)
    student_exam_id = get_student_exam_id(student_code, room_code)
    
     # Lấy thời lượng bài thi
    conn = get_db_connection()
    cursor1 = conn.cursor(dictionary=True, buffered=True)
    
    cursor1.execute("SELECT duration_minutes FROM exam_rooms WHERE room_code = %s", (room_code,))
    exam_room = cursor1.fetchone()
    if not exam_room:
        cursor1.close()
        conn.close()
        return "Không tìm thấy thông tin phòng thi", 404
    duration = exam_room['duration_minutes']
    
    
    
    is_late = is_student_late(room_code, student_code)
    
    cursor2 = conn.cursor(dictionary=True, buffered=True)
    cursor2.execute("""
    SELECT se.start_time, er.duration_minutes, er.open_time, er.grace_period_minutes
    FROM student_exams se
    JOIN exam_rooms er ON se.room_code = er.room_code
    WHERE se.room_code = %s AND se.student_code = %s
""", (room_code, student_code))
    exam_info = cursor2.fetchone()

    if not exam_info:
        cursor2.close()
        conn.close()
        return "Không tìm thấy thông tin bài thi", 404

    duration = exam_info['duration_minutes']
    start_time = exam_info['start_time']
    grace_period_minutes = exam_info['grace_period_minutes']
    room_start_time = exam_info['open_time']
    room_end_time = room_start_time + timedelta(minutes=duration + grace_period_minutes)

# Kiểm tra sinh viên từng bị kick chưa
    cursor2.execute("""
    SELECT status, first_start_time
    FROM control_students
    WHERE room_code = %s AND student_code = %s AND status = 'kicked'
    """, (room_code, student_code))
    control_info = cursor2.fetchone()

    if control_info:
        first_start_time = control_info['first_start_time']
        kicked_end_time = first_start_time + timedelta(minutes=duration)
        end_time = min(room_end_time, kicked_end_time)
    elif is_late:
        room_remaining_time = room_end_time - datetime.now()
    # Thời gian còn lại không vượt quá thời lượng bài thi
        end_time = datetime.now() + min(room_remaining_time, timedelta(minutes=duration))
    
    # Xóa status='late' sau khi xử lý
        clear_late_status(student_code, room_code)
    else:
        end_time = start_time + timedelta(minutes=duration)

    start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
    end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')

    cursor2.close()
    conn.close()

    
    ########
    # cursor2 = conn.cursor(dictionary=True, buffered=True)
    # cursor2.execute("""
    # SELECT se.start_time, er.duration_minutes
    # FROM student_exams se
    # JOIN exam_rooms er ON se.room_code = er.room_code
    # WHERE se.room_code = %s AND se.student_code = %s
    # """, (room_code, student_code))
    # result = cursor2.fetchone()
    # if not result:
    #     cursor2.close()
    #     conn.close()
    #     return "Không tìm thấy thông tin bài thi", 404
    
    
    # start_time = result['start_time']
    
    # cursor2.close()
    # conn.close()
    ########

    # ✅ Tính toán thời điểm kết thúc
    
    #end_time = start_time + timedelta(minutes=duration)
    #end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
    #start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
    # end_time = datetime.now() + timedelta(minutes=duration)
    # end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')

    # Lấy danh sách câu hỏi của mã đề này
    exam_code_id = sel_exam_code_id_by_code(exam_code)  # Lấy ID từ mã đề như "8-003"
    
    questions = get_exam_questions_by_code_id(exam_code_id)

    return render_template('student_take_exam.html', student_exam_id=student_exam_id, questions=questions,
                           student_name=student_name, student_code=student_code, room_code=room_code, exam_code=exam_code,end_time=end_time_str, student_start_time=start_time_str)


# Route: Xử lý khi sinh viên nộp bài
@student_bp.route('/submit-exam/<room_code>', methods=['POST'])
def submit_exam(room_code):
    print("🚀 Hàm submit_exam đã được gọi!")

    student_exam_id = request.form.get('student_exam_id')
    exam_code = request.form.get('exam_code')
    print(f"🔸 answer_mapping: {exam_code}")
    room_code = request.form.get('room_code') 
    
    exam_code_id = get_exam_code_id_by_code(exam_code)
    print(f"🔸 answer_mapping: {exam_code_id}")
    
    is_advanced = is_advanced_exam_set(exam_code_id)
    print(f"🧠 Đề nâng cao? {is_advanced}")
    
    student_code = get_student_code_by_exam_and_room(student_exam_id, room_code)


    if is_advanced:
        # ✅ Chấm theo phân bổ nâng cao
        score, total, correct = grade_advanced_exam(request.form, exam_code_id, room_code)
    else:

     score = 0
     total = 0
     correct = 0
     print("📥 request.form:", request.form)

     for key, value in request.form.items():
         print(f"🧪 Key: {key} - Value: {value}")
         if key.startswith('question_'):
            question_id = int(key.split('_')[1])
            #question_id = key.split('_')[1]
            selected_answer = value.strip().upper()
            print(f"🎯 Xử lý câu hỏi ID: {question_id}, Chọn: {selected_answer}")

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT answer_a, answer_b, answer_c, answer_d, correct_answer
                FROM exam_question_map
                WHERE question_id = %s AND exam_code_id = %s
            """, (question_id, exam_code_id))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            print(f"🧪 Kết quả truy vấn: {row}")

            if not row:
                continue  # Không tìm thấy câu hỏi

            answer_mapping = {
                "A": row["answer_a"],
                "B": row["answer_b"],
                "C": row["answer_c"],
                "D": row["answer_d"]
            }
            print(f"🔸 answer_mapping: {answer_mapping}")

            selected_answer_text = answer_mapping.get(selected_answer)
            print(f"🔸 selected_answer_text: {selected_answer_text}")
            correct_answer = row["correct_answer"]
            #correct = selected_answer == row["correct_answer"]

            print(f"🔸 correct_answer: {correct_answer}")

            is_correct = selected_answer == correct_answer
            print(f"📌 So sánh: Chọn: {selected_answer_text} | Đúng: {correct_answer}")
            print(f"✅ Kết quả: {'Đúng' if is_correct else 'Sai'}\n")

            
            print(f"🎯 QID: {question_id}, Chọn: {selected_answer} ({selected_answer_text}), Đúng: {correct_answer}, KQ: {is_correct}")



            if is_correct:
                correct += 1
            total += 1
            
            print("in ra score", score)
            print("in ra total", total)
            print("in ra student code", student_exam_id)
           
            score = round((correct / total) * 10, 2) if total > 0 else 0  # ✅ Điểm trên thang 10
            
            save_student_answer(student_exam_id, question_id, selected_answer, is_correct)
           

            #save_student_answer(student_exam_id, room_code, exam_code_id, question_id, selected_answer, is_correct)
    update_student_exam_score(student_code, room_code, score)
    
    
     
            
     #return render_template("exam_result.html", score=score, total=total, correct=correct)

            #save_student_answer(student_exam_id, room_code, exam_code_id, question_id, selected_answer, is_correct)

    # cập nhật điểm và trạng thái đã nộp
    
    socketio.emit('student_submitted', {
        'student_code': student_code,
        'room_code': room_code,
        'score': score
    }, namespace='/webrtc')

    response = make_response(render_template("exam_result.html", score=score, total=total, correct=correct))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
def clear_late_status(student_code, room_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM control_students
        WHERE student_code = %s AND room_code = %s AND status = 'late'
    """, (student_code, room_code))
    
    conn.commit()
    cursor.close()
    conn.close()

def grade_advanced_exam(form_data, exam_code_id, room_code):
    correct_counts = {'difficulty_easy': 0, 'difficulty_medium': 0, 'difficulty_hard': 0}
    total_counts = {'difficulty_easy': 0, 'difficulty_medium': 0, 'difficulty_hard': 0}
    
    difficulty_map = {
    0: 'difficulty_easy',
    1: 'difficulty_medium',
    2: 'difficulty_hard'
}
    seen_questions = set()  # ✅ Tránh tính trùng câu hỏi


    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    for key, value in form_data.items():
        print(f"📥 Dữ liệu người dùng gửi lên: {key} = {value}")

        if key.startswith('question_'):
            question_id = int(key.split('_')[1])
            selected_answer = value.strip().upper()

            cursor.execute("""
                SELECT eqm.answer_a, eqm.answer_b, eqm.answer_c, eqm.answer_d, eqm.correct_answer,
                       q.difficulty
                FROM exam_question_map eqm
                JOIN questions q ON eqm.question_id = q.id
                WHERE eqm.question_id = %s AND eqm.exam_code_id = %s
            """, (question_id, exam_code_id))
            row = cursor.fetchone()
            print(f"✅ Câu hỏi {question_id}: Đáp án đúng = {row['correct_answer']}, Mức độ = {row['difficulty']}")

            if not row:
                print(f"⚠️ Không tìm thấy câu hỏi ID {question_id} trong mã đề {exam_code_id}")
                continue

            answer_mapping = {
                "A": row["answer_a"],
                "B": row["answer_b"],
                "C": row["answer_c"],
                "D": row["answer_d"]
            }
            selected_text = answer_mapping.get(selected_answer)
            #correct = selected_text == row["correct_answer"]
            correct = selected_answer == row["correct_answer"]

            print(f"📝 Người chọn: {selected_answer}, So với đáp án đúng: {row['correct_answer']} => {'✅ Đúng' if correct else '❌ Sai'}")
            
            raw_level = row["difficulty"]

            #level = row["difficulty"]
            level = difficulty_map.get(raw_level)
            if level not in total_counts:
                continue

            total_counts[level] += 1
            if correct:
                correct_counts[level] += 1
                print(f"📊 Mức độ: {level} | Tổng số câu: {total_counts[level]} | Đúng: {correct_counts[level]}")
            else:
               print(f"📊 Mức độ: {level} | Tổng số câu: {total_counts[level]} | Sai")


    cursor.close()
    conn.close()

    # Lấy thông số phân bổ điểm từ phòng
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT difficulty_easy_pct, difficulty_medium_pct, difficulty_hard_pct
        FROM exam_rooms WHERE room_code = %s
    """, (room_code,))
    room_config = cursor.fetchone()
    print(f"⚙️ Phân bổ điểm theo phòng thi: {room_config}")

    cursor.close()
    conn.close()
    
    # sửa chấm điểm từ đoạn này nhé
    # Xác định các mức độ thực sự có mặt (vượt qua giá trị khởi tạo mặc định là 1)
    
    present_levels = [level for level, count in total_counts.items() if count > 0]

    # Tính tổng phần trăm người dùng đã phân bổ cho các mức độ có mặt
    total_pct = sum(room_config.get(f"{level}_pct", 0) for level in present_levels)

    def calc_score(level):
        if level not in present_levels or total_counts[level] == 0:
            return 0
        original_pct = room_config.get(f"{level}_pct", 0)
        print(f"in ra original: {original_pct}")
        adjusted_pct = (original_pct / total_pct) * 100
        print(f"in ra adjusted_pct: {adjusted_pct}")
        
        #return 
        
        print(f"📦 Tổng số câu theo mức độ: {total_counts}")
        print(f"🎯 Số câu đúng theo mức độ: {correct_counts}")
        print(f"🔍 Các mức độ có mặt: {present_levels}")
        print(f"📐 Tổng phần trăm các mức độ có mặt: {total_pct}")
        
        # ghi log
        
        return (adjusted_pct / 100) * (correct_counts[level] / total_counts[level])

    total_score = sum(calc_score(level) for level in present_levels)
    print(f"📐 total socre là : {total_score}")
    return round(total_score * 10, 2), sum(total_counts.values()), sum(correct_counts.values())
    #     pct = room_config.get(f"{level}_pct", 0)
    #     if total_counts[level] == 0:
    #         return 0
    #     return (pct / 100) * (correct_counts[level] / total_counts[level])

    # total_score = calc_score('difficulty_easy') + calc_score('difficulty_medium') + calc_score('difficulty_hard')
    # return round(total_score * 10, 2), sum(total_counts.values())
def check_submitted_and_redirect(student_code, room_code):
    if not student_code or not room_code:
        flash("Thiếu thông tin sinh viên hoặc phòng thi.")
        return "thiếu thông tin cá nhân"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True,  buffered=True)
    cursor.execute("""
        SELECT submitted
        FROM student_exams
        WHERE student_code = %s AND room_code = %s
    """, (student_code, room_code))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row and row.get("submitted") == 1:
        flash("Bạn đã nộp bài. Không thể quay lại phòng thi.")
        return "Bạn đã nộp bài"  # 🔁 Trang kết quả

    return None  # ✅ Cho phép tiếp tục
def is_student_late(room_code, student_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT status 
        FROM control_students 
        WHERE room_code = %s AND student_code = %s
    """, (room_code, student_code))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result['status'] == 'late' if result else False


