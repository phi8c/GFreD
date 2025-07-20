from app.controllers.extensions import socketio
from controllers.room_controller import  join_exam
from flask_socketio import SocketIO, emit, join_room
from gen_questions import get_db_connection
from models.exam_model import create_exam_room, assign_exam_code, get_exam_sets, get_room_id_by_code
from controllers.room_controller import is_thpt_2025_exam



print("✅ socket_events.py đã được import")


@socketio.on('join_room', namespace='/webrtc')
def handle_join(data):
    room = data['room']
    join_room(room)
    #emit('new-student-joined', data, room=data['roomcode'])
    print(f"Client joined room {room}")

@socketio.on('offer', namespace='/webrtc')
def handle_offer(data):
    socketio.emit('offer', data, room=data['room'], namespace='/webrtc')

@socketio.on('answer', namespace='/webrtc')
def handle_answer(data):
    socketio.emit('answer', data, room=data['room'], namespace='/webrtc')

@socketio.on('ice-candidate', namespace='/webrtc')
def handle_ice(data):
    socketio.emit('ice-candidate', data, room=data['room'], namespace='/webrtc')
joined_students_per_room = {}
@socketio.on('new-student-joined', namespace='/webrtc')
def handle_new_student(data):
    room = data['room']
    student_code = data.get('student_code')

    # Khởi tạo nếu chưa có
    if room not in joined_students_per_room:
        joined_students_per_room[room] = set()

    # ✅ Nếu đã có sinh viên này, bỏ qua
    if student_code in joined_students_per_room[room]:
        print(f"⚠️ Sinh viên {student_code} đã vào phòng {room}, bỏ qua emit.")
        return

    # ✅ Nếu chưa có, thêm và emit
    joined_students_per_room[room].add(student_code)
    print("📩 Nhận new-student-joined từ sinh viên", data)
    emit('new-student-joined', data, room=data['room'], namespace='/webrtc')
    
    # from here
# đoạn này mới thêm vào

@socketio.on('teacher-rejoined', namespace='/webrtc')
def handle_teacher_rejoined(data):
    print(" đã gọi tới socket load lại")
    room_code = data.get("roomCode")

    if room_code:
        # Gửi lại yêu cầu tới tất cả sinh viên trong phòng
        print(f"👨‍🏫 Giảng viên vào lại, yêu cầu sinh viên gửi lại stream trong room {room_code}")
        emit('resend-stream', {}, room=room_code)



@socketio.on('approve_student', namespace='/webrtc')
def handle_approve_student(data):
    room_code = data.get('room')
    student_code = data.get('student_code')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ✅ Ghi trạng thái allowed
    cursor.execute("""
    UPDATE control_students
    SET status = 'allowed'
    WHERE room_code = %s AND student_code = %s
    ORDER BY created_at DESC
    LIMIT 1
    """, (room_code, student_code))
    conn.commit()

    # 🔍 Lấy exam_set_id từ room để chia mã đề
    cursor.execute("""
        SELECT exam_set_id FROM exam_rooms WHERE room_code = %s
    """, (room_code,))
    room = cursor.fetchone()
    if not room:
        cursor.close()
        conn.close()
        return

    exam_set_id = room['exam_set_id']

    # 📄 Tìm phiên thi mới nhất
    cursor.execute("""
        SELECT id, exam_code FROM student_exams
        WHERE room_code = %s AND student_code = %s
        ORDER BY id DESC LIMIT 1
    """, (room_code, student_code))
    exam = cursor.fetchone()

    if not exam:
        cursor.close()
        conn.close()
        return

    student_exam_id = exam['id']
    exam_code = exam['exam_code']

    # ⚠️ Nếu chưa có mã đề, thì chia mã đề
    if not exam_code:
        exam_code = assign_exam_code(room_code, exam_set_id)
        cursor.execute("""
            UPDATE student_exams SET exam_code = %s
            WHERE id = %s
        """, (exam_code, student_exam_id))
        conn.commit()

    # 🧠 Kiểm tra loại đề
    exam_type = 'default'
    if is_thpt_2025_exam(exam_set_id):
        exam_type = 'thpt2025'

    cursor.close()
    conn.close()
    
    
    print("in ra mã phòng", room_code)

    # 📡 Gửi thông tin về client
    emit('student_approved', {
        'student_code': student_code,
        'student_exam_id': student_exam_id,
        'exam_code': exam_code,
        'room_code': room_code,
        'exam_type': exam_type
    }, room=student_code)

    # Gửi sự kiện cho chính sinh viên này để cho phép vào
    


@socketio.on('reject_student', namespace='/webrtc')
def handle_reject_student(data):
    room_code = data.get('room')
    student_code = data.get('student_code')
    print(f"❌ Giảng viên từ chối {student_code} vào phòng {room_code}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE control_students
        SET status = 'kicked'
        WHERE room_code = %s AND student_code = %s
    """, (room_code, student_code))
    conn.commit()
    cursor.close()
    conn.close()

    # Gửi sự kiện cho sinh viên biết bị từ chối (tuỳ bạn có cần hay không)
    emit('student_rejected', {'room_code': room_code}, room=student_code)
    
@socketio.on('request_approval', namespace='/webrtc')
def handle_request_approval(data):
    student_code = data.get('student_code')
    full_name = data.get('full_name')
    class_name = data.get('class_name')
    room_code = data.get('room')

    print(f"📩 Sinh viên {student_code} ({full_name}) đang yêu cầu vào lại phòng {room_code}")
    
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Kiểm tra nếu đã có thì cập nhật trạng thái về 'pending', ngược lại thì tạo mới
    cursor.execute("""
        SELECT id FROM control_students 
        WHERE room_code = %s AND student_code = %s
    """, (room_code, student_code))

    existing = cursor.fetchone()
    if existing:
        cursor.execute("""
            UPDATE control_students
            SET status = 'pending'
            WHERE room_code = %s AND student_code = %s
        """, (room_code, student_code))
    else:
        cursor.execute("""
            INSERT INTO control_students (room_code, student_code, status)
            VALUES (%s, %s, 'pending')
        """, (room_code, student_code))
    conn.commit()
    cursor.close()
    conn.close()

    # Gửi yêu cầu phê duyệt đến giảng viên
    emit('student_waiting_approval', {
        'student_code': student_code,
        'full_name': full_name,
        'class_name': class_name,
        'room_code': room_code
    }, room=room_code)
    
@socketio.on('kick_student', namespace='/webrtc')
def handle_kick_student(data):
    room_code = data.get('room')
    student_code = data.get('student_code')

    print(f"👢 Giảng viên kick {student_code} khỏi phòng {room_code}")

    # 1. Cập nhật trạng thái trong CSDL
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO control_students (room_code, student_code, status)
        VALUES (%s, %s, 'kicked')
        ON DUPLICATE KEY UPDATE status = 'kicked', created_at = NOW()
    """, (room_code, student_code))
    
    # XÓA phiên thi student_exams
    cursor.execute("""
        DELETE FROM student_exams
        WHERE room_code = %s AND student_code = %s
    """, (room_code, student_code))

    conn.commit()
    cursor.close()
    conn.close()

    # 2. Gửi socket cho sinh viên bị kick (dựa vào student_code là room riêng)
    emit('kicked', {'reason': 'Bạn đã bị giảng viên đưa ra khỏi phòng thi.'}, room=student_code, namespace='/webrtc')
    # Gửi socket cho giảng viên để xóa video sinh viên đó
    emit('remove_student', {'student_code': student_code}, room=room_code, namespace='/webrtc')


    # 3. (Tùy chọn) Gửi phản hồi lại giảng viên nếu cần
    #emit('kick_success', {'student_code': student_code}, room=request.sid)


    # Gửi sự kiện cho tất cả giảng viên trong phòng
#### sự kiện ban


@socketio.on('ban_student', namespace='/webrtc')
def handle_ban_student(data):
    room_code = data.get('room')
    student_code = data.get('student_code')

    print(f"🚫 Giảng viên ban {student_code} khỏi phòng {room_code}")

    # 1. Cập nhật trạng thái trong CSDL thành 'blocked'
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO control_students (room_code, student_code, status)
        VALUES (%s, %s, 'blocked')
        ON DUPLICATE KEY UPDATE status = 'blocked', created_at = NOW()
    """, (room_code, student_code))

    # Có thể XÓA phiên thi nếu muốn giống như kick
    cursor.execute("""
        DELETE FROM student_exams
        WHERE room_code = %s AND student_code = %s
    """, (room_code, student_code))

    conn.commit()
    cursor.close()
    conn.close()

    # 2. Gửi thông báo socket cho sinh viên bị ban (join theo student_code là tên room)
    emit('banned', {'reason': 'Bạn đã bị cấm khỏi phòng thi.'}, room=student_code, namespace='/webrtc')
    # Gửi socket cho giảng viên để xóa video sinh viên đó
    emit('remove_student', {'student_code': student_code}, room=room_code, namespace='/webrtc')






#### kết thúc sự kiên ban
    




# kết thúc đoạn mới thêm vào
#### ĐOẠN NÀY MỚI THÊM VÀO

# RAM cache log tạm thời (nếu cần)
room_logs = {}

@socketio.on('log_event', namespace='/webrtc')
def handle_log_event(data):
    print("Nhận được room log")
    room = data['room_code']
    log_entry = {
        'student': data['student_name'],
        'type': data['type'],
        'detail': data.get('detail', ''),
        'time': data['timestamp']
    }

    # Lưu vào RAM nếu cần
    if room not in room_logs:
        room_logs[room] = []
    room_logs[room].append(log_entry)

    print(f"[LOG] {log_entry}")  # In server

    # Gửi log đến giảng viên nếu đang xem phòng này
    emit("new_log", log_entry, room=room)
    
    


#### KẾT THÚC SOCKETS MỚI THÊM VÀO

    
@socketio.on('join_room', namespace='/room')
def join_room_event(data):
    room = data['room']
    join_room(room)
    emit('new_student_joined', data, room=room)

@socketio.on('offer', namespace='/room')
def handle_offer(data):
    emit('offer', data, room=data['room'], include_self=False)

@socketio.on('answer', namespace='/room')
def handle_answer(data):
    emit('answer', data, room=data['room'])

@socketio.on('ice-candidate', namespace='/room')
def handle_ice_candidate(data):
    emit('ice-candidate', data, room=data['room'])
    