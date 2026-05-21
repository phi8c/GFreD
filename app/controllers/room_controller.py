from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app,  after_this_request, session
from models.exam_model import create_exam_room, assign_exam_code, get_exam_sets, get_room_id_by_code, get_original_questions_thpt2025, update_student_exam_score
import random
from gen_questions import get_db_connection, create_exam_set
from utils.export_exam_utils import export_exam_package, export_exam_set_to_xlsx, import_questions_from_xlsx, render_exam_to_docx, render_exam_to_pdf, render_answer_to_docx, render_exam_with_answers_to_docx, export_student_exam_to_docx, export_original_exam_to_pdf, export_original_exam_to_docx, export_exam_with_answers_to_pdf, render_exam_with_answers_to_docx, export_original_exam_to_pdf_advance, export_question_set_to_docx, export_question_set_to_docx_scd, render_exam_to_docx_scd, export_exam_to_pdf_scd, export_original_exam_to_docx_no_answers, export_original_exam_to_pdf_advance_no_answers
from flask import send_file
from datetime import datetime, timedelta
from app.controllers.extensions import socketio
import io
import zipfile
from flask import jsonify
import openpyxl
from controllers.mail_event import send_otp_email
from flask_login import current_user, login_required
import tempfile
import shutil
import os
from werkzeug.utils import secure_filename
from io import BytesIO





room_bp = Blueprint('room_bp', __name__)

@login_required

@room_bp.route('/manage-room/<room_code>')
def manage_exam_room(room_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # 1. Lấy thông tin phòng thi
    cursor.execute("""
        SELECT created_at, duration_minutes, grace_period_minutes, open_time
        FROM exam_rooms
        WHERE room_code = %s
    """, (room_code,))
    room_info = cursor.fetchone()

    if not room_info:
        cursor.close()
        conn.close()
        return "❌ Không tìm thấy phòng thi."

    # 2. Tính thời điểm bắt đầu chính thức (sau grace period) và thời điểm kết thúc
    now = datetime.now()
    official_start_time = room_info['open_time'] 
    start_time_str = official_start_time.strftime('%Y-%m-%dT%H:%M:%S')
    
   
    # Tính thời gian kết thúc từ open_time
        
        
    end_time = (
    room_info['open_time']
    + timedelta(minutes=room_info['grace_period_minutes'])
    + timedelta(minutes=room_info['duration_minutes'])
    )
    exam_end_time = end_time.strftime('%Y-%m-%dT%H:%M:%S')
    # official_start_time = room_info['created_at'] + timedelta(minutes=room_info['grace_period_minutes'])
    # end_time = official_start_time + timedelta(minutes=room_info['duration_minutes'])
    
    
    cursor.execute("""
        SELECT student_name, student_code, status, camera_approved
        FROM student_exams
        WHERE room_code = %s
    """, (room_code,))
    students = cursor.fetchall()
    print("📋 students từ DB:")
    for s in students:
     print(s)
    cursor.close()
    conn.close()
    
    #end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
    

    return render_template("manage_room.html", room_code=room_code, students=students, exam_end_time=exam_end_time, exam_start_time=start_time_str)




@room_bp.route('/exam-room', methods=['GET'])
def exam_ui():
    #return render_template('generate_room.html')
    user_id = current_user.id  
    print("in ra user_id ở exam-ui", user_id)
    
    selected_exam_set_id = request.args.get('exam_set_id', type=int)
    exam_sets = get_exam_sets(user_id=user_id)  # Giả sử đang test với user_id = 1
    return render_template('generate_room.html', exam_sets=exam_sets, selected_exam_set_id=selected_exam_set_id)

@room_bp.route('/create-room', methods=['POST'])
@login_required
def create_room():
    subject_name = request.form.get('subject_name')
    duration = int(request.form.get('duration'))
    exam_set_id = int(request.form.get('exam_set_id'))
    
    open_time_str = request.form.get('open_time')  # ISO format: yyyy-MM-ddTHH:mm
    grace_period = int(request.form.get('grace_period'))
    
    
    easy_str = request.form.get('easy_percentage')
    medium_str = request.form.get('medium_percentage')
    hard_str = request.form.get('hard_percentage')
    
    print("📥 Dữ liệu phân bổ điểm nhận được từ form:")
    print(f"    ➤ easy_percentage   = {easy_str}")
    print(f"    ➤ medium_percentage = {medium_str}")
    print(f"    ➤ hard_percentage   = {hard_str}")
    
    #return "✅ Đang kiểm tra nhận đủ dữ liệu hay không."
    
    easy = int(easy_str) if easy_str else None
    medium = int(medium_str) if medium_str else None
    hard = int(hard_str) if hard_str else None
    # easy = int(request.form.get('difficulty_easy_pct', 20))
    # medium = int(request.form.get('difficulty_medium_pct', 50))
    # hard = int(request.form.get('difficulty_hard_pct', 30))

    # Convert open_time to datetime object
    open_time = datetime.strptime(open_time_str, '%Y-%m-%dT%H:%M')
    
    #user_id = current_user.id 
    user_id = current_user.id
    print("🔐 create_room - user_id:", user_id)
    
    #### mới thêm vào
    
    error_msg = is_open_time_invalid(open_time, user_id , duration)
    if error_msg:
        flash(error_msg, "danger")  # nếu dùng flash
        return render_template(
        "generate_room.html", 
        error=error_msg,
          # nếu muốn giữ lại dữ liệu đã nhập trước đó
    )

    
    
    #### kết thúc mới thêm vào

    #user_id = 1  # Mặc định khi chưa có đăng nhập
    room_code = create_exam_room(subject_name, duration, user_id, exam_set_id, open_time,
        grace_period, easy, medium, hard)
    
    # đoạn mã để import danh sách sinh vieenn này mới được thêm vào này mới được thêm vào
        # Giả sử bạn thêm vào form tạo phòng một input type="file" name="student_file"
    file = request.files.get('student_file')
    if file:
        try:
            print("📥 Đã nhận file:", file.filename)
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            for row in sheet.iter_rows(min_row=2, values_only=True):
                print(f"📄 Dòng {row}: {row}")
                student_id, full_name, email = row
                if not student_id or not full_name or not email:
                    print(f"⚠️ Bỏ qua dòng {row} do thiếu dữ liệu.")
                    continue
                # Truy xuất room_id từ room_code
                room_id = get_room_id_by_code(room_code)
                #print("🏷️ room_id truy xuất được:", room_id)

                # Kiểm tra trùng trong cùng phòng
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                "SELECT 1 FROM room_students WHERE room_id = %s AND student_id = %s AND email = %s",
                (room_id, student_id, email)
                 )
                exists = cursor.fetchone()
                if not exists:
                 cursor.execute(
                "INSERT INTO room_students (room_id, student_id, full_name, email) VALUES (%s, %s, %s, %s)",
                (room_id, student_id, full_name, email)
                )

                conn.commit()
                cursor.close()
                conn.close()
        except Exception as e:
            print("❌ Lỗi khi import danh sách sinh viên:", e)
            return f"Lỗi khi import file Excel: {e}"

    
    
    # kết thúc của đoạn mã import danh sách sinh viên
    
    

    # room_code = create_exam_room(subject_name, duration, user_id, exam_set_id, open_time,
    #     grace_period, easy, medium, hard)

    #return render_template('room_created.html', room_code=room_code)
    return redirect(url_for('room_bp.manage_exam_room', room_code=room_code))

@room_bp.route('/join-room', methods=['GET', 'POST'])
def join_exam():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        student_id = request.form.get('student_id')
        class_name = request.form.get('class_name')
        room_code = request.form.get('room_code')
        room_codes = request.form.get('room_code')
        email_input = request.form.get('email')
        student_code = request.form.get('student_id')
        
        
        
        
        
         # 1. Tìm exam_room theo room_code
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM exam_rooms WHERE room_code = %s", (room_code,))
        exam_room = cursor.fetchone()

        if not exam_room:
            return "❌ Mã phòng thi không tồn tại."
        
        result_if_submitted = check_submitted_and_redirect(student_id, room_code)
        if result_if_submitted:
            return "bạn đã thi rồi không được vào lại"
        # từ đoạn này là thay đổi logic kiểm tra thời gian ########
        
        cursor.execute("""
            SELECT status FROM control_students
            WHERE room_code = %s AND student_code = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (room_code, student_id))
        status_record = cursor.fetchone()

        bypass_time_check = False
        if status_record:
            if status_record['status'] == 'blocked':
                cursor.close()
                conn.close()
                return "🚫 Bạn đã bị chặn khỏi phòng thi này và không được phép tham gia."
            elif status_record['status'] == 'kicked':
                bypass_time_check = True  # ✅ Cho phép tiếp tục mà không kiểm tra thời gian

        # ✅ Nếu không bị kicked thì mới kiểm tra thời gian
        if not bypass_time_check:
            open_time = exam_room['open_time']
            now = datetime.now()

            if now < open_time:
                return redirect(url_for('room_bp.waiting_room',
                    student_name=full_name,
                    student_id=student_id,
                    email=email_input,
                    room_code=room_code
                ))

            grace_period = exam_room.get('grace_period_minutes', 20)
            allowed_until = open_time + timedelta(minutes=grace_period)
            if now > allowed_until:
                cursor.close()
                conn.close()
                #return "⏰ Đã quá thời gian cho phép vào phòng thi."
                return redirect(url_for('room_bp.late_waiting_room',
                    student_name=full_name,
                    student_id=student_id,
                    email=email_input,
                    room_code=room_code
                ))

        
        
        
        # thay đổi đến đoạn này #######
            


        # ✅ Kiểm tra khung thời gian vào phòng
        # open_time = exam_room['open_time']
        
        # now = datetime.now()

        # if now < open_time:
        #     return redirect(url_for('room_bp.waiting_room', 
        #     student_name=full_name,
        #     student_id=student_id,
        #     email=email_input,
        #     room_code=room_code
        #      ))
        # grace_period = exam_room.get('grace_period_minutes', 20)
        

        # allowed_until = open_time + timedelta(minutes=grace_period)
        # now = datetime.now()

        # if now > allowed_until:
        #     cursor.close()
        #     conn.close()
        #     return "⏰ Đã quá thời gian cho phép vào phòng thi."

        # 1. Tìm exam_room theo room_code
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM exam_rooms WHERE room_code = %s", (room_code,))
        exam_room = cursor.fetchone()
        
        # new
        # ✅ So khớp mã sinh viên và email với dữ liệu đã import
        cursor.execute("""
            SELECT * FROM room_students
            WHERE room_id = %s AND student_id = %s AND email = %s
        """, (exam_room['id'], student_id, email_input))
        student_check = cursor.fetchone()

        if not student_check:
            return "❌ Bạn không có trong danh sách phòng thi. Vui lòng kiểm tra lại mã sinh viên và email."
        
        # newv

        if not exam_room:
            return "❌ Mã phòng thi không tồn tại."
        exam_set_id = exam_room['exam_set_id']  # ✅ Lấy exam_set_id của phòng
        duration = exam_room['duration_minutes']
        room_id = exam_room['id']
        
         # ✅ Lưu thông tin sinh viên vào bảng students (nếu chưa tồn tại)
         
        student_db_id = find_or_create_student(full_name, student_id, class_name) 
         
        # cursor.execute("""
        #     INSERT INTO students (full_name, student_id, class_name)
        #     VALUES (%s, %s, %s)
        # """, (full_name, student_id, class_name))
        # conn.commit()
        # vừa mới sửa

        # 3. Gán mã đề ngẫu nhiên (ví dụ: 001–004)
        exam_code = assign_exam_code(room_code, exam_set_id)
         # 📌 Khởi tạo phiên làm bài
        cursor.execute("""
            INSERT INTO student_exams (student_name, student_code, room_code, exam_code, exam_set_id, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (full_name, student_id, room_code, exam_code, exam_set_id))
        conn.commit()

        # ➕ Lưu vào session nếu cần (sử dụng Flask session)

        cursor.close()
        conn.close()
        socketio.emit('student_joined', {
        'student_name': full_name,
        'student_code': student_id,
        'room_code': room_code
         }, namespace='/room')

       
        if not exam_room:
            return "❌ Mã phòng thi không tồn tại."
        
        #
        
        # 📌 Lấy email từ bảng room_students (danh sách sinh viên của phòng)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
        SELECT email FROM room_students 
        WHERE room_id = %s AND student_id = %s
        """, (exam_room['id'], student_id))
        student = cursor.fetchone()

        if not student:
         return "❌ Không tìm thấy sinh viên trong danh sách phòng."

        email = student['email']
        

# ✅ Sinh mã OTP ngẫu nhiên 6 chữ số
        otp_code = str(random.randint(100000, 999999))

# ✅ Lưu OTP vào bảng otp_verification
        cursor.execute("""
       INSERT INTO otp_verifications (room_id, student_id, email, otp_code, expires_at)
       VALUES (%s, %s, %s, %s, NOW())
       """, (room_id, student_id, email, otp_code))
        conn.commit()
        
        session["student_name"] = full_name
        session["student_code"] = student_id
        
        
        
        session["room_code"] = room_codes
        
        
        #
        
        send_otp_email(email, otp_code)
        
        print("in ra exam_code trong tham gia thi", exam_code)


        # 👉 Chuyển sang student_exam.html, truyền lại thông tin
        return render_template("student_exam.html", room_code=room_code,
                               student_name=full_name, student_code=student_id, exam_code=exam_code)

    return render_template("join_exam.html")
@room_bp.route('/exam/<room_code>', methods=['GET', 'POST'])
def enter_exam_room(room_code):
    
     if request.method == 'POST':
        # student_name = request.form.get('student_name')
        # student_code = request.form.get('student_code')
        student_name = session.get("student_name", "")
        student_code = session.get("student_code", "")
        otp_input = request.form.get('otp_code')
        room_code = request.form.get('room_code')
        assigned_exam_code = request.form.get('exam_code')
        print("nhan duoc room_code", room_code)
        # 1. Lấy email của sinh viên từ bảng otp_verification
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM exam_rooms WHERE room_code = %s", (room_code,))
        room = cursor.fetchone()

        if not room:
            cursor.close()
            conn.close()
            return "❌ Mã phòng không tồn tại."

        room_id = room['id']

        cursor.execute("""
            SELECT email, otp_code, expires_at 
            FROM otp_verifications 
            WHERE room_id = %s AND student_id = %s
            ORDER BY expires_at DESC
            LIMIT 1
        """, (room_id, student_code))
        otp_record = cursor.fetchone()

        if not otp_record:
            cursor.close()
            conn.close()
            return "❌ Không tìm thấy yêu cầu OTP. Vui lòng quay lại và nhập lại thông tin."

        
        if datetime.now() > otp_record['expires_at'] + timedelta(minutes=5):  # hết hạn sau 5 phút
            cursor.close()
            conn.close()
            return "⏰ Mã OTP đã hết hạn. Vui lòng quay lại và thử lại."

        if otp_input != otp_record['otp_code']:
            cursor.close()
            conn.close()
            return "❌ Mã OTP không chính xác. Vui lòng kiểm tra lại."

        # 👉 OTP hợp lệ: cho phép làm bài
        # Có thể xóa bản ghi nếu muốn (bảo mật hơn)
        cursor.execute("""
            DELETE FROM otp_verifications 
            WHERE room_id = %s AND student_id = %s
        """, (room_id, student_code))
        conn.commit()
        
        

        # 🔍 Truy vấn để lấy exam_set_id từ exam_rooms
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT exam_set_id FROM exam_rooms WHERE room_code = %s", (room_code,))
        room = cursor.fetchone()
        cursor.close()
        conn.close()

        if not room:
            return "❌ Không tìm thấy phòng thi!"

        exam_set_id = room['exam_set_id']
        
        # đoạn này mới thêm vào để kiểm tra sinh viên có bị đuổi, chặn hay không
        
        # 🔍 Kiểm tra trạng thái thi của sinh viên
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
        SELECT status FROM control_students
        WHERE room_code = %s AND student_code = %s
        ORDER BY created_at DESC
        LIMIT 1
        """, (room_code, student_code))

        status_record = cursor.fetchone()

        if status_record:
            status = status_record['status']
    
            if status == 'blocked':
                cursor.close()
                conn.close()
                return "🚫 Bạn đã bị chặn khỏi phòng thi này và không được phép tham gia."

            elif status == 'kicked':
        # Ghi nhận lại yêu cầu vào phòng với trạng thái 'waiting'
                cursor.execute("""
                INSERT INTO control_students (room_code, student_code, status)
                VALUES (%s, %s, 'pending')
                """, (room_code, student_code))
                conn.commit()

        # Gửi sự kiện socket tới giảng viên để cập nhật danh sách chờ duyệt
                socketio.emit('student_waiting_approval', {
                'student_code': student_code,
                'student_name': student_name,
                'room_code': room_code
                }, namespace='/webrtc')
                
                now = datetime.now()
        
                update_exam_start_time(student_code, room_code, now)

                cursor.close()
                conn.close()
                
                
                return render_template('waiting_approval.html', student_code=student_code, room_code=room_code, exam_code=assigned_exam_code, student_name=student_name)
            

        # Nếu không có bản ghi nào hoặc trạng thái bình thường thì cho phép tiếp tục
        # Nếu không có bản ghi nào hoặc trạng thái bình thường thì cho phép tiếp tục
        cursor.close()
        conn.close()
        # Cho phép vào phòng (return None hoặc code tiếp theo xử lý)
        
        

        
        
        
        
        
        # kết thúc iểm tra sinh viên có bị đuổi, chặn hay không
        
        

        # ✅ Gán mã đề theo bộ đề request.form.get('room_code')
        #assigned_exam_code = assign_exam_code(room_code, exam_set_id)
        #assigned_exam_code = request.args.get('exam_code')
        print("exam_code trong enter_exam_room", assigned_exam_code)
        
        
        now = datetime.now()
        
        update_exam_start_time(student_code, room_code, now)
        
        
        if is_student_doing_other_exam_today(student_code, room_code):
            return "❌ Bạn đang tham gia phòng thi khác. Không được vào thêm phòng mới."
        
        
        
        if is_thpt_2025_exam(exam_set_id):
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
        SELECT id FROM student_exams
        WHERE student_code = %s AND room_code = %s
        ORDER BY id DESC
        LIMIT 1
        """, (student_code, room_code))
            student_exam = cursor.fetchone()
            cursor.close()
            conn.close()

            if not student_exam:
                return "❌ Không tìm thấy thông tin làm bài của sinh viên."
            return redirect(url_for('exam_hs.thpt2025_exam', room_code=room_code, student_exam_id=student_exam['id']))
        else:
            print("in ra room_code enter exam romm", room_code)
            return redirect(url_for('student_bp.start_exam',
                                student_name=student_name,
                                student_code=student_code,
                                room_code=room_code,
                                exam_code=assigned_exam_code))

     return render_template('student_exam.html', room_code=room_code)
@room_bp.route('/start-exam/<int:student_id>/<int:exam_room_id>/<exam_code>', methods=['GET'])
def start_exam(student_id, exam_room_id, exam_code):
    
    return f"Sinh viên ID: {student_id}, Mã phòng: {exam_room_id}, Mã đề: {exam_code}"
@room_bp.route('/select-exam-set', methods=['GET'])
def select_exam_set():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, set_name FROM exam_sets")
    exam_sets = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('export_exam.html', exam_sets=exam_sets)



@room_bp.route('/export-exam', methods=['GET'])
def export_exam_view():
    exam_set_id = request.args.get('exam_set_id')
    if not exam_set_id:
        return "⚠️ Không tìm thấy bộ đề cần xuất.", 400

    zip_path = export_exam_package(int(exam_set_id))
    return send_file(zip_path, as_attachment=True)
@room_bp.route('/api/exam-set-type/<int:exam_set_id>')
def get_exam_set_type(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT DISTINCT difficulty FROM questions
        WHERE exam_set_id = %s
    """, (exam_set_id,))
    levels = [row['difficulty'] for row in cursor.fetchall()]
    conn.close()

    is_advanced = set(levels) & { 1, 2} != set()  # đề nâng cao nếu có đủ các mức
    return jsonify({'is_advanced': is_advanced})
@room_bp.route('/upcoming-rooms')
@login_required
def upcoming_exam_rooms():
    user_id = current_user.id  
    if not user_id:
        return redirect(url_for('auth_bp.login'))  # hoặc xử lý chưa đăng nhập

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT room_code, subject_name, open_time, duration_minutes
        FROM exam_rooms
        WHERE created_by_user_id = %s AND open_time > NOW()
        ORDER BY open_time ASC
    """, (user_id,))

    rooms = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('upcoming_rooms.html', rooms=rooms)




@room_bp.route('/lounge-room')
def waiting_room():
    student_name = request.args.get('student_name')
    student_id = request.args.get('student_id')
    email = request.args.get('email')
    room_code = request.args.get('room_code')

    if not all([student_name, student_id, email, room_code]):
        return "Thiếu thông tin truy cập phòng chờ.", 400

    # Lấy thông tin exam_room
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM exam_rooms WHERE room_code = %s", (room_code,))
    exam_room = cursor.fetchone()
    cursor.close()
    conn.close()

    if not exam_room:
        return "❌ Không tìm thấy thông tin phòng thi.", 404
    
    # open_time là kiểu datetime từ DB
    open_time_str = exam_room['open_time'].strftime('%Y-%m-%dT%H:%M:%S')
    #exam_set_id = room['exam_set_id']
    room_id = exam_room['id']


    # ✅ Khởi tạo phiên thi nếu cần
    #start_exam_session(student_name, student_id, email, room_code, exam_room)

    return render_template("lounge_room.html", 
        student_name=student_name,
        student_id=student_id,
        email=email,
        room_code=room_code,
        open_time=open_time_str,
        room_id = room_id
    )
@room_bp.route('/enter-exam')
def enter_exam():
    student_name = request.args.get("student_name")
    student_id = request.args.get("student_id")
    email = request.args.get("email")
    room_code = request.args.get("room_code")
    student_code = request.args.get("student_id")
    #room_id = request.args.get("room_id")

    # Lấy thông tin phòng thi
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM exam_rooms WHERE room_code = %s", (room_code,))
    exam_room = cursor.fetchone()
    cursor.close()
    conn.close()

    if not exam_room:
        return "❌ Không tìm thấy phòng thi."
    room_id = exam_room['id']
    print("in ra room_id ở trong enter", room_id)

    # ✅ Gọi lại hàm khởi tạo phiên thi
    start_exam_session(
        student_name=student_name,
        student_id=student_id,
        email=email,
        room_code=room_code,
        exam_room=exam_room,
        room_id=room_id
    )
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
    SELECT exam_code FROM student_exams
    WHERE student_code = %s AND room_code = %s
""", (student_id, room_code))
    row = cursor.fetchone()
    conn.close()

    if row:
        exam_code = row['exam_code']
        print(f"[INFO] Exam code của sinh viên {student_id} trong phòng {room_code} là: {exam_code}")
    else:
        print(f"[WARN] Không tìm thấy exam_code cho sinh viên {student_id} trong phòng {room_code}")

    # ✅ Chuyển sang giao diện làm bài
    
    print("bắt đầu chuyển trang")
    
    return render_template("student_exam.html",
                           student_name=student_name,
                           student_code=student_id,
                           room_code=room_code,
                           room_id = room_id,
                           exam_code = exam_code
                           )


@room_bp.route('/late-waiting-room')
def late_waiting_room():
    student_name = request.args.get('student_name')
    student_id = request.args.get('student_id')
    email = request.args.get('email')
    room_code = request.args.get('room_code')

    if not all([student_name, student_id, email, room_code]):
        return "Thiếu thông tin truy cập phòng chờ muộn.", 400

    # Lấy thông tin exam_room
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM exam_rooms WHERE room_code = %s", (room_code,))
    exam_room = cursor.fetchone()

    if not exam_room:
        return "❌ Không tìm thấy phòng thi.", 404

    room_id = exam_room['id']

    # ✅ Ghi log vào control_students với trạng thái 'late'
    cursor.execute("""
        INSERT INTO control_students (student_code, room_code, status)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE status = 'late'
    """, (student_id, room_code, 'late'))
    conn.commit()
    cursor.close()
    conn.close()

    # ✅ Emit socket tới giảng viên
    # hoặc wherever bạn khai báo socket
    socketio.emit('late_join_request', {
        'student_name': student_name,
        'student_id': student_id,
        'email': email,
        'room_code': room_code
    }, namespace= '/webrtc')

    return render_template("late_waiting_room.html", 
        student_name=student_name,
        student_id=student_id,
        email=email,
        room_code=room_code,
        room_id=room_id
    )



# ROUTE NÀY MỚI THÊM VÀO ĐỂ XUẤT CÂU HỎI XLXS
@room_bp.route("/exam_incomplete")
def exam_incomplete():
    return render_template("exam_incomplete.html")

@room_bp.route('/export-exam-questions-xlsx')
@login_required
def export_exam_questions_xlsx_view():
    """
    Xử lý yêu cầu xuất bộ đề thi ra file Excel (.xlsx).
    Người dùng cần cung cấp exam_set_id và user_id qua tham số URL.
    """
    # 1. Lấy tham số từ yêu cầu HTTP
    # 'type=int' đảm bảo rằng giá trị được chuyển đổi thành số nguyên
    exam_set_id = request.args.get('exam_set_id')
    user_id = current_user.id 

    # 2. Kiểm tra các tham số bắt buộc
    if not exam_set_id or not user_id:
        return "⚠️ Thiếu thông tin bộ đề (exam_set_id) hoặc người dùng (user_id) cần xuất.", 400

    # 3. Tạo một thư mục tạm thời để lưu file Excel.
    # tempfile.mkdtemp() sẽ tạo một thư mục duy nhất và an toàn trong thư mục tạm của hệ thống.
    # File sẽ được tạo trong thư mục này.
    temp_dir_for_export = tempfile.mkdtemp()
    exported_file_path = None # Khởi tạo biến để lưu đường dẫn file đã xuất

    try:
        # 4. Gọi hàm điều phối chính để xuất file Excel.
        # Hàm này sẽ xác định loại bộ đề (MCQ thuần/nâng cao/THPT2025)
        # và tạo file Excel tương ứng trong 'temp_dir_for_export'.
        # Nó trả về đường dẫn tuyệt đối của file Excel đã được tạo.
        exported_file_path = export_exam_set_to_xlsx(user_id, exam_set_id, temp_dir_for_export)
        print("in ra hàm sau khi truy vấn", exported_file_path)
        
        # 5. Lấy tên file từ đường dẫn đầy đủ để gửi về cho người dùng
        file_name = os.path.basename(exported_file_path)

        # 6. Gửi file về trình duyệt của người dùng
        # 'as_attachment=True' buộc trình duyệt phải tải file về
        # 'download_name' đặt tên file khi người dùng tải về
        
        
        @after_this_request
        def cleanup(response):
            try:
                if exported_file_path and os.path.exists(os.path.dirname(exported_file_path)):
                    shutil.rmtree(os.path.dirname(exported_file_path))
                elif temp_dir_for_export and os.path.exists(temp_dir_for_export):
                    shutil.rmtree(temp_dir_for_export)
            except Exception as cleanup_err:
                print(f"Lỗi khi dọn dẹp thư mục tạm: {cleanup_err}")
                return response
        return send_file(exported_file_path, as_attachment=True, download_name=file_name)

    except ValueError as e:
        # Xử lý trường hợp không tìm thấy câu hỏi hoặc các lỗi liên quan đến dữ liệu đầu vào
        return f"⚠️ {e}", 404
    except Exception as e:
        # Xử lý các lỗi chung khác xảy ra trong quá trình xuất file
        print(f"Lỗi khi xuất file Excel: {e}") # Log lỗi để debug
        return "⚠️ Có lỗi xảy ra khi xuất file.", 500
    
    
def check_submitted_and_redirect(student_code, room_code):
    if not student_code or not room_code:
        flash("Thiếu thông tin sinh viên hoặc phòng thi.")
        return "thiếu thông tin cá nhân"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    cursor.execute("""
        SELECT 1
        FROM student_exams
        WHERE student_code = %s AND room_code = %s
        LIMIT 1
    """, (student_code, room_code))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        flash("Bạn đã vào thi. Không thể quay lại phòng thi.")
        return "Bạn đã nộp bài"  # 🔁 Trang kết quả

    return None  # ✅ Cho phép tiếp tục

    



# KẾT THÚC ROUTE XUẤT CÂU HỎI XLXS
# route nay để ghi log

@room_bp.route('/log-event', methods=['POST'])
def log_event():
    data = request.get_json()
    print(f"[LOG]: {data['message']}")
    return '', 204

# đây là hàm để tham gia phòng thi






def start_exam_session(student_name, student_id, email, room_code, exam_room, room_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 🔍 Kiểm tra xem đã có bản ghi student_exams chưa
    cursor.execute("""
        SELECT * FROM student_exams
        WHERE room_code = %s AND student_code = %s
    """, (room_code, student_id))
    existing_exam = cursor.fetchone()
    
    

    if existing_exam:
        student_exam_id = existing_exam['id']
        print(f"✅ Sinh viên {student_id} đã có phiên thi: {student_exam_id}")
    else:
        # 🧠 Gán mã đề
        exam_code = assign_exam_code(room_code, exam_room['exam_set_id'])

        # 📝 Tạo bản ghi mới
        cursor.execute("""
            INSERT INTO student_exams (student_name, student_code, room_code, exam_code, exam_set_id, start_time, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            student_name,
            student_id,
            room_code,
            exam_code,
            exam_room['exam_set_id'],
            datetime.now()
        ))
        conn.commit()
        student_exam_id = cursor.lastrowid

        # 📡 Emit tới giảng viên
        socketio.emit('student_joined', {
            'student_name': student_name,
            'student_code': student_id,
            'room_code': room_code
        }, namespace='/room')

    # 📧 Gửi OTP
    otp_code = str(random.randint(100000, 999999))

    cursor.execute("""
        INSERT INTO otp_verifications (room_id, student_id, email, otp_code, expires_at)
        VALUES (%s, %s, %s, %s, NOW() + INTERVAL 5 MINUTE)
    """, (room_id, student_id, email, otp_code))
    conn.commit()
    
    session["student_name"] = student_name
    session["student_code"] = student_id
        
        
        
    session["room_code"] = room_code

    send_otp_email(email, otp_code)

    cursor.close()
    conn.close()

    return student_exam_id



# kết thúc hàm tham gia phòng thi


# tới đây

#route này để kiểm tra xem bộ đề có những mức độ nào


@room_bp.route("/api/exam-set-levels/<int:exam_set_id>")
def get_exam_set_levels(exam_set_id):
    
    level_map = {
        0: "easy",
        1: "medium",
        2: "hard"
    }

    conn = get_db_connection()
    cursor = conn.cursor()

    # Truy vấn các mức độ duy nhất trong đề
    cursor.execute("SELECT DISTINCT difficulty FROM questions WHERE exam_set_id = %s", (exam_set_id,))
    raw_levels = [row[0] for row in cursor.fetchall()]

    print(f"📥 Kiểm tra mức độ đề ID {exam_set_id}: các mức độ raw: {raw_levels}")

    # Chuyển từ số -> tên mức độ nếu hợp lệ
    levels = [level_map[level] for level in raw_levels if level in level_map]

    print(f"✅ Các mức độ hợp lệ chuyển đổi: {levels}")

    cursor.close()
    conn.close()

    return jsonify({"levels": levels})

# route này kiểm tra tất cả sinh viên đã nộp bài chưa

@room_bp.route('/api/check-all-submitted/<room_code>')
def check_all_submitted(room_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 🔍 Truy vấn lấy room_id từ room_code
    cursor.execute("""
        SELECT id FROM exam_rooms
        WHERE room_code = %s
    """, (room_code,))
    room = cursor.fetchone()

    if not room:
        cursor.close()
        conn.close()
        return jsonify({"error": "Không tìm thấy phòng thi."}), 404

    room_id = room['id']

    # ✅ Tổng số sinh viên theo bảng room_students
    cursor.execute("""
        SELECT COUNT(*) AS total FROM room_students
        WHERE room_id = %s
    """, (room_id,))
    total = cursor.fetchone()['total']

    # ✅ Số sinh viên đã nộp bài từ student_exams
    cursor.execute("""
        SELECT COUNT(*) AS submitted FROM student_exams
        WHERE room_code = %s AND submitted = 1
    """, (room_code,))
    submitted = cursor.fetchone()['submitted']

    cursor.close()
    conn.close()

    return jsonify({
        "total": total,
        "submitted": submitted,
        "all_submitted": submitted == total
    })


# kết thúc kiểm tra tất cả sinh viên nộp bài



# kết thúc của route kiểm tra mức độ của bộ đề

# route này để sử lý thêm sinh viên bị kick vào bảng dưu liệu
@room_bp.route('/api/kick_student', methods=['POST'])
def kick_student():
    data = request.get_json()
    room_code = data.get('room_code')
    student_code = data.get('student_code')
    action = data.get('action')  # 'kick' hoặc 'kick_and_block'

    if not all([room_code, student_code, action]):
        return jsonify({"success": False, "message": "Thiếu dữ liệu."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    if action == 'kick':
        # Kick: status = kicked, blocked = FALSE
        cursor.execute("""
            INSERT INTO student_exam_status (room_code, student_code, status, blocked)
            VALUES (%s, %s, 'kicked', FALSE)
            ON DUPLICATE KEY UPDATE status = 'kicked', blocked = FALSE
        """, (room_code, student_code))
    elif action == 'kick_and_block':
        # Kick + block: status = kicked, blocked = TRUE
        cursor.execute("""
            INSERT INTO student_exam_status (room_code, student_code, status, blocked)
            VALUES (%s, %s, 'kicked', TRUE)
            ON DUPLICATE KEY UPDATE status = 'kicked', blocked = TRUE
        """, (room_code, student_code))
    else:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Hành động không hợp lệ."}), 400

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True, "message": "Đã cập nhật trạng thái sinh viên."})
# route này mới thêm vào

@room_bp.route('/api/kicked-students/<room_code>', methods=['GET'])
def get_kicked_students(room_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT cs.student_code
        FROM control_students cs
        
        WHERE cs.room_code = %s AND cs.status = 'kicked'
    """, (room_code,))
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(students)
# kết thúc route mới thêm vào

@room_bp.route('/unban-student', methods=['POST'])
def unban_student():
    data = request.get_json()
    room_code = data.get('room_code')
    student_code = data.get('student_id')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE control_students
        SET status = 'pending'
        WHERE room_code = %s AND student_code = %s
    """, (room_code, student_code))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Student marked as pending again'}), 200

# kết thúc route thêm sinh viên bị kick

@room_bp.route('/ban-student', methods=['POST'])
def ban_student():
    data = request.get_json()
    room_code = data.get('room_code')
    student_code = data.get('student_id')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE control_students
        SET status = 'blocked'
        WHERE room_code = %s AND student_code = %s
    """, (room_code, student_code))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Student has been blocked'}), 200


# Trả về danh sách sinh viên bị "kick" và đang chờ duyệt (chưa bị blocked


@room_bp.route('/end-exam/<room_code>', methods=['POST'])
def end_exam(room_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy ID của phòng thi từ room_code
    cursor.execute("SELECT id FROM exam_rooms WHERE room_code = %s", (room_code,))
    room = cursor.fetchone()

    if not room:
        cursor.close()
        conn.close()
        return "❌ Không tìm thấy phòng thi.", 404

    room_id = room['id']

    # ✅ Cập nhật trạng thái phòng thi
    cursor.execute("""
        UPDATE exam_rooms
        SET status = 'archived'
        WHERE id = %s
    """, (room_id,))
    conn.commit()

    cursor.close()
    conn.close()

    # 🔁 Chuyển hướng sang trang thống kê chi tiết
    return redirect(url_for('statistical.show_students_in_room', room_id=room_id))

@room_bp.route('/goto-statistical/<room_code>', methods=['GET', 'POST'])
def redirect_to_statistical(room_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy id của phòng thi
    cursor.execute("SELECT id FROM exam_rooms WHERE room_code = %s", (room_code,))
    room = cursor.fetchone()

    if not room:
        cursor.close()
        conn.close()
        return "❌ Không tìm thấy phòng thi.", 404

    # ✅ Cập nhật trạng thái phòng thi thành 'archived'
    cursor.execute("""
        UPDATE exam_rooms
        SET status = 'archived'
        WHERE room_code = %s
    """, (room_code,))
    conn.commit()

    cursor.close()
    conn.close()

    # ✅ Chuyển hướng đến trang thống kê chi tiết
    return redirect(url_for("statistical.show_students_in_room", room_id=room["id"]))


@room_bp.route('/api/pending_approvals/<room_code>')
def get_pending_approvals(room_code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT student_code
        FROM student_exam_status
        WHERE room_code = %s AND status = 'kicked' AND blocked = FALSE
    """, (room_code,))
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(students)

@room_bp.route('/api/students-in-room/<room_code>', methods=['GET'])
def get_students_in_room(room_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Lấy danh sách sinh viên đã được duyệt trong phòng thi
    cursor.execute("""
        SELECT student_code, student_name
        FROM student_exams
        WHERE room_code = %s AND status = 'doing'
    """, (room_code,))
    
    rows = cursor.fetchall()
    student_list = [{"code": row[0], "name": row[1]} for row in rows]

    cursor.close()
    conn.close()
    print("in ra studentcde:", student_list )

    return jsonify({"students": student_list})





# kêt thúc Trả về danh sách sinh viên bị "kick" và đang chờ duyệt (chưa bị blocked

@room_bp.route('/api/approve_student', methods=['POST'])
def approve_student():
    data = request.get_json()
    room_code = data.get('room_code')
    student_code = data.get('student_code')
    approve = data.get('approve')  # True = duyệt, False = từ chối

    if not all([room_code, student_code]):
        return jsonify({"success": False, "message": "Thiếu dữ liệu."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    if approve:
        # Nếu được duyệt, cập nhật status = 'approved'
        cursor.execute("""
            UPDATE student_exam_status
            SET status = 'approved'
            WHERE room_code = %s AND student_code = %s
        """, (room_code, student_code))
    else:
        # Nếu từ chối, xóa luôn bản ghi (hoặc cập nhật lại status nếu muốn)
        cursor.execute("""
            DELETE FROM student_exam_status
            WHERE room_code = %s AND student_code = %s
        """, (room_code, student_code))

    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True, "message": "Cập nhật thành công."})

@room_bp.route('/api/statistics/<room_code>')
def get_score_statistics(room_code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Lấy tên sinh viên và điểm số từ bảng student_exams kèm room_code
        cursor.execute("""
            SELECT se.student_name, se.score
            FROM student_exams se
            
            WHERE se.room_code = %s AND se.score IS NOT NULL
        """, (room_code,))
        rows = cursor.fetchall()

        high = []
        good = []
        low = []
        distribution = [0] * 11  # từ 0 đến 10 điểm

        for row in rows:
            score = row["score"]
            name = row["student_name"]

            # Nhóm điểm
            if score >= 9:
                high.append(name)
            elif score >= 8:
                good.append(name)
            elif score < 5:
                low.append(name)

            # Phổ điểm (làm tròn xuống)
            index = int(score)
            if 0 <= index <= 10:
                distribution[index] += 1

        return jsonify({
            "success": True,
            "groups": {
                "high": high,
                "good": good,
                "low": low
            },
            "score_distribution": distribution
        })

    except Exception as e:
        print("Lỗi khi truy vấn thống kê điểm:", e)
        return jsonify({"success": False, "error": str(e)}), 500
    
# route này để import file câu hỏi

ALLOWED_EXTENSIONS = {'xlsx'}

def allowed_file(filename):
    """Kiểm tra định dạng file có hợp lệ không."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@room_bp.route('/import-exam-questions-xlsx', methods=['GET', 'POST'])
@login_required
def import_exam_questions_xlsx_view():
    """
    Xử lý việc tải lên và nhập câu hỏi từ file Excel.
    """
    # Đảm bảo thư mục UPLOAD_FOLDER tồn tại.
    # Nên tạo thư mục này một lần khi ứng dụng khởi động,
    # hoặc có thể tạo ở đây nếu nó không tồn tại.
    # Tuy nhiên, cách tốt nhất là tạo nó một lần khi ứng dụng khởi tạo.
    # Ví dụ: os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
    # bạn có thể thêm dòng này vào file app.py của mình sau khi thiết lập config

    if request.method == 'POST':
        # 1. Kiểm tra xem có file được gửi lên không
        if 'file' not in request.files:
            flash('⚠️ Không có file nào được chọn để tải lên.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # 2. Kiểm tra tên file rỗng
        if file.filename == '':
            flash('⚠️ Tên file không được để trống.', 'danger')
            return redirect(request.url)
        
        # 3. Kiểm tra định dạng file và xử lý
        if file and allowed_file(file.filename):
            # 4. Lấy exam_set_id và user_id từ form
            set_name = request.form.get('set_name', type=str)
            user_id = current_user.id
            exam_set_id = create_exam_set(set_name, user_id)
            

            if not exam_set_id or not user_id:
                flash('⚠️ Thiếu ID bộ đề hoặc ID người dùng để nhập câu hỏi.', 'danger')
                return redirect(request.url)

            # 5. Lưu file tạm thời vào thư mục UPLOAD_FOLDER đã cấu hình
            filename = secure_filename(file.filename)
            # Sử dụng current_app.config để lấy đường dẫn UPLOAD_FOLDER
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            
            try:
                file.save(file_path) # Lưu file upload
                
                # 6. Gọi hàm import chính để xử lý file
                # Hàm import_questions_from_xlsx sẽ chịu trách nhiệm xóa file sau khi xử lý xong
                import_results = import_questions_from_xlsx(file_path, exam_set_id, user_id)

                # 7. Hiển thị kết quả nhập cho người dùng
                if import_results["failed_rows"]:
                    flash(f"Đã nhập thành công {import_results['imported_questions']} câu hỏi. Có {len(import_results['failed_rows'])} lỗi.", 'warning')
                    for msg in import_results["failed_rows"]:
                        flash(msg, 'warning') # Hiển thị chi tiết lỗi của từng hàng
                else:
                    flash(f"✅ Đã nhập thành công {import_results['imported_questions']} câu hỏi vào bộ đề ID {exam_set_id}.", 'success')
                
                # Hiển thị thêm các thông báo chung từ quá trình import (nếu có)
                for msg in import_results["messages"]:
                    flash(msg, 'info')

            except Exception as e:
                flash(f"⛔️ Có lỗi không mong muốn xảy ra trong quá trình nhập file: {e}", 'danger')
                print(f"Lỗi chi tiết khi import file: {e}") # In lỗi ra console để debug
            finally:
                # Hàm import_questions_from_xlsx đã có logic xóa file sau khi xử lý xong.
                # Đoạn code này chỉ là một lớp bảo vệ dự phòng nếu có lỗi xảy ra
                # trước khi file được chuyển giao cho hàm import_questions_from_xlsx.
                # Tuy nhiên, trong trường hợp này, nếu hàm import_questions_from_xlsx
                # không được gọi thành công, file vẫn sẽ nằm lại ở UPLOAD_FOLDER.
                # Tốt nhất là kiểm tra và xóa file bên trong hàm import_questions_from_xlsx
                # như chúng ta đã làm.
                pass # Không cần os.remove(file_path) ở đây nữa, vì hàm import đã làm

            return redirect(url_for('room_bp.import_exam_questions_xlsx_view'))
        else:
            flash('⚠️ Loại file không hợp lệ. Chỉ chấp nhận định dạng .xlsx', 'danger')
            return redirect(request.url)
    
    # Hiển thị form upload khi người dùng truy cập bằng phương thức GET
    return render_template('handle_insert_questions.html')



@room_bp.route('/export-exam-code/<int:exam_code_id>', methods=['GET'])
def export_exam_code(exam_code_id):
    export_format = request.args.get("format", "pdf")  # "pdf" hoặc "docx"

    # Truy vấn dữ liệu mã đề
    data = get_exam_code_data(exam_code_id)
    # for key, value in data.items():
    #     print(key, ":", value)

    if not data:
        return "Không tìm thấy dữ liệu mã đề", 404
    
    

    # Tạo file tương ứng
    if export_format == "docx":
        doc = render_exam_to_docx(data)
        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)
        filename = f"ma_de_{data['exam_code']}.docx"
        return send_file(buf, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    elif export_format == "pdf":
        buf = export_exam_with_answers_to_pdf(data)  # Đã trả về BytesIO
        filename = f"ma_de_{data['code']}.pdf"
        return send_file(buf, as_attachment=True, download_name=filename, mimetype="application/pdf")

    else:
        return "Định dạng không hỗ trợ. Chỉ hỗ trợ pdf hoặc docx", 400
    
@room_bp.route('/export-answer-code/<int:exam_code_id>', methods=['GET'])
def export_answer_code(exam_code_id):
    export_format = request.args.get("format", "pdf")  # "pdf" hoặc "docx"
    data = get_exam_code_data(exam_code_id)
    if not data:
        return "Không tìm thấy mã đề", 404

    if export_format == "docx":
        doc = render_exam_to_docx_scd(data)
        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name=f"dapan_{data['exam_code']}.docx",
                         mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    elif export_format == "pdf":
        buf = export_exam_to_pdf_scd(data)
        return send_file(buf, as_attachment=True, download_name=f"dapan_{data['exam_code']}.pdf",
                         mimetype="application/pdf")
    else:
        return "Chỉ hỗ trợ định dạng docx hoặc pdf", 400
    
    
    
@room_bp.route("/export-docx/questions/<int:exam_set_id>")
def export_questions_docx(exam_set_id):
    try:
        # Bước 1: Lấy danh sách câu hỏi gốc (MCQ)
        data = get_full_mcq_questions_by_exam_set(exam_set_id)

        if not data:
            return "Không tìm thấy câu hỏi nào để xuất.", 404

        # Bước 2: Gọi hàm xuất DOCX
        buffer = export_question_set_to_docx(data)

        filename = f"Bo_de_{exam_set_id}.docx"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        return f"Lỗi khi tạo file: {str(e)}", 500
@room_bp.route("/export-docx-scd/questions/<int:exam_set_id>")
def export_questions_docx_scd(exam_set_id):
    try:
        # Bước 1: Lấy danh sách câu hỏi gốc
        data = get_full_mcq_questions_by_exam_set(exam_set_id)

        if not data:
            return "Không tìm thấy câu hỏi nào để xuất.", 404

        # Bước 2: Gọi hàm xuất DOCX dạng bảng
        buffer = export_question_set_to_docx_scd(data)

        filename = f"Bo_de_{exam_set_id}.docx"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        return f"Lỗi khi tạo file: {str(e)}", 500










# kết thúc route import file câu hỏi


# vừa mới thêm vào

def find_or_create_student(full_name, student_id, class_name):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Kiểm tra student_id đã tồn tại
    cursor.execute("SELECT id FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()

    if student:
        student_db_id = student['id']
    else:
        cursor.execute("""
            INSERT INTO students (full_name, student_id, class_name)
            VALUES (%s, %s, %s)
        """, (full_name, student_id, class_name))
        conn.commit()
        student_db_id = cursor.lastrowid

    cursor.close()
    conn.close()
    return student_db_id


# hàm này mới thêm vào

def is_thpt_2025_exam(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM tf_questions WHERE exam_set_id = %s LIMIT 1", (exam_set_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None

def update_exam_start_time(student_code, room_code, start_time):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        UPDATE student_exams
        SET start_time = %s
        WHERE student_code = %s AND room_code = %s
        """,
        (start_time, student_code, room_code)
    )
    
    conn.commit()
    cursor.close()
    conn.close()



# kết thúc đoạn vừa thêm vào
def is_student_doing_other_exam_today(student_code, current_room_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT se.room_code
        FROM student_exams se
        JOIN exam_rooms er ON se.room_code = er.room_code
        WHERE se.student_code = %s
          AND se.start_time IS NOT NULL
          AND se.submitted = 0
          AND NOW() BETWEEN er.open_time AND (
              er.open_time + INTERVAL (er.grace_period_minutes + er.duration_minutes) MINUTE
          )
          AND se.room_code != %s
    """, (student_code, current_room_code))

    result = cursor.fetchone()

    cursor.close()
    conn.close()
    return result is not None


def is_open_time_invalid(open_time, user_id, duration_minutes):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Làm tròn thời gian tới phút (xóa giây và micro giây)
    open_time = open_time.replace(second=0, microsecond=0)
    now = datetime.now().replace(second=0, microsecond=0)

    # ⛔ Kiểm tra nếu open_time trong quá khứ
    if open_time < now:
        return "⛔ Thời gian mở phòng phải là hiện tại hoặc tương lai."

    # ✅ Tính thời gian kết thúc của phòng thi mới
    new_start = open_time
    new_end = open_time + timedelta(minutes=duration_minutes)

    # 🔍 Lấy danh sách các phòng do user tạo từ hôm nay trở về sau
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    cursor.execute("""
        SELECT open_time, duration_minutes
        FROM exam_rooms
        WHERE created_by_user_id = %s AND open_time >= %s
    """, (user_id, today))
    existing_rooms = cursor.fetchall()

    for room in existing_rooms:
        existing_start = room['open_time'].replace(second=0, microsecond=0)
        existing_end = existing_start + timedelta(minutes=room['duration_minutes'])

        # Nếu thời gian trùng nhau (giao nhau)
        if (new_start < existing_end and new_end > existing_start):
            return "⛔ Thời gian mở phòng bị trùng với một phòng thi khác của bạn."

    cursor.close()
    conn.close()

    return None  # Không có lỗi

def get_exam_code_data(exam_code_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy thông tin mã đề và exam_set_id
    cursor.execute("""
        SELECT ec.id AS exam_code_id, ec.code AS exam_code, ec.exam_set_id
        FROM exam_codes ec
        WHERE ec.id = %s
    """, (exam_code_id,))
    code_info = cursor.fetchone()
    if not code_info:
        cursor.close()
        conn.close()
        return None

    exam_set_id = code_info['exam_set_id']

    # -------- Lấy câu hỏi MCQ từ exam_question_map ----------
    cursor.execute("""
        SELECT q.id AS question_id,
               q.question_text,
               eqm.answer_a,
               eqm.answer_b,
               eqm.answer_c,
               eqm.answer_d,
               eqm.correct_answer,
               eqm.question_order,
               eqm.chapter,
               eqm.difficulty
        FROM exam_question_map eqm
        JOIN questions q ON q.id = eqm.question_id
        WHERE eqm.exam_code_id = %s
        ORDER BY eqm.question_order
    """, (exam_code_id,))
    mcq_questions = cursor.fetchall()

    # --------- Kiểm tra xem có TF hoặc SA không ------------
    cursor.execute("""
        SELECT hqm.id, hqm.question_type, hqm.original_question_id, hqm.position
        FROM hs_question_map hqm
        WHERE hqm.exam_code_id = %s
        ORDER BY hqm.position
    """, (exam_code_id,))
    hs_mappings = cursor.fetchall()

    tf_questions = []
    sa_questions = []

    for m in hs_mappings:
        if m['question_type'] == 'tf':
            cursor.execute("SELECT * FROM tf_questions WHERE id = %s", (m['original_question_id'],))
            tf_q = cursor.fetchone()
            if tf_q:
                cursor.execute("""
                    SELECT label, content, is_true, position
                    FROM hs_tf_statements
                    WHERE hs_map_id = %s
                    ORDER BY position
                """, (m['id'],))
                statements = cursor.fetchall()
                tf_q['statements'] = statements
                tf_questions.append({'position': m['position'], **tf_q})

        elif m['question_type'] == ' ':
            cursor.execute("SELECT * FROM short_answer_questions WHERE id = %s", (m['original_question_id'],))
            sa_q = cursor.fetchone()
            if sa_q:
                sa_questions.append({'position': m['position'], **sa_q})

    cursor.close()
    conn.close()

    # Xác định loại đề
    if tf_questions or sa_questions:
        question_type = "thpt_2025"
    else:
        question_type = "mcq"

    return {
        "exam_code": code_info['exam_code'],
        "exam_code_id": code_info['exam_code_id'],
        "exam_set_id": code_info['exam_set_id'],
        "question_type": question_type,
        "mcq_questions": mcq_questions,
        "tf_questions": tf_questions,
        "sa_questions": sa_questions
    }

def get_full_mcq_questions_by_exam_set(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            id,
            question_text,
            answer_a,
            answer_b,
            answer_c,
            answer_d,
            correct_answer,
            chapter,
            difficulty
           
        FROM questions
        WHERE exam_set_id = %s
        ORDER BY id
    """
    cursor.execute(query, (exam_set_id,))
    questions = cursor.fetchall()

    cursor.close()
    conn.close()
    return questions

@room_bp.route('/export-original-exam/<int:exam_set_id>', methods=['GET'])
def export_original_exam(exam_set_id):
    # Lấy tham số định dạng đầu ra: pdf hoặc docx
    export_format = request.args.get("format", "pdf")

    # Kiểm tra dạng đề dựa trên dữ liệu
    data_thpt = get_original_questions_thpt2025(exam_set_id)
    has_tf_or_sa = data_thpt.get("tf") or data_thpt.get("SA")
    exam_type = "thpt_2025" if has_tf_or_sa else "mcq"

    if exam_type == "mcq":
        data = get_full_mcq_questions_by_exam_set(exam_set_id)
    else:
        data = data_thpt  # dữ liệu đã lấy ở trên

    # Xuất file
    if export_format == "docx":
        doc = export_original_exam_to_docx_no_answers(exam_type, data)
        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)
        filename = f"de_goc_{exam_set_id}.docx"
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return send_file(buf, as_attachment=True, download_name=filename, mimetype=mime_type)

    elif export_format == "pdf":
        buf = export_original_exam_to_pdf_advance_no_answers(exam_type, data)
        filename = f"de_goc_{exam_set_id}.pdf"
        return send_file(buf, as_attachment=True, download_name=filename, mimetype="application/pdf")

    else:
        return "Định dạng không hỗ trợ. Chỉ hỗ trợ pdf hoặc docx", 400


### hàm xuất folder chứa thông tin bài làm sinh viên













