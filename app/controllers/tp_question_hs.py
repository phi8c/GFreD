# exam2025.py

import os
import uuid
from flask import Blueprint, request, jsonify, current_app, render_template, redirect, url_for
from werkzeug.utils import secure_filename

from extract_text import extract_chapters_from_pdf, extract_chapters_from_docx, extract_chapters_from_file, extract_chapters_from_pdffs, extract_chapters_from_pdf_advance
from generates_questions import generate_mcq_questions, generate_true_false_questions, generate_short_answer_questions, generate_tf_with_images

from models.exam_model import save_mcq_questions, save_tf_questions, save_short_answer_questions

from flask_login import current_user, login_required
import random
from gen_questions import get_db_connection

from gen_questions import create_exam_set
from collections import defaultdict

highschool_bp = Blueprint('highschool', __name__)


@highschool_bp.route('/create_questions_hs')
@login_required
def create_questions_view():
    return render_template('hs_questions.html')


@highschool_bp.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'Không có file nào được gửi.'}), 400

    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()

    upload_dir = os.path.join(current_app.root_path, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    saved_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}{file_ext}")
    file.save(saved_path)

    # Tạo thư mục ảnh riêng cho file này
    image_dir = os.path.join(current_app.root_path, 'uploads', 'images', uuid.uuid4().hex)
    os.makedirs(image_dir, exist_ok=True)

    if file_ext == ".pdf":
        chapters = extract_chapters_from_pdffs(saved_path, image_dir)
        print("in ra chapter khi trích xuất file", chapters)
    elif file_ext == ".docx":
        chapters = extract_chapters_from_docx(saved_path, image_dir)
    else:
        return jsonify({'error': 'Chỉ hỗ trợ file .pdf và .docx'}), 400

    # Trả về số chương và thông tin để phân bổ
    chapter_info = [
        {"title": ch["title"], "text_length": len(ch["text"])} for ch in chapters
    ]
    return jsonify({
        "num_chapters": len(chapters),
        "chapter_info": chapter_info,
        "chapters": chapters  # có thể loại bỏ nếu frontend không cần toàn bộ text/images
    })
    
def distribute_counts(total, num_parts):
    base = total // num_parts
    remainder = total % num_parts
    return [base + (1 if i < remainder else 0) for i in range(num_parts)]

def to_web_path(abs_path):
    uploads_root = os.path.abspath("uploads")
    try:
        rel_path = os.path.relpath(abs_path, uploads_root).replace("\\", "/")
        return "/uploads/" + rel_path
    except:
        return None  # nếu không xử lý được

@highschool_bp.route('/generate_hs_questions', methods=['POST'])
@login_required
def generate_hs_questions():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'Không có file nào được gửi.'}), 400

    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()

    upload_dir = os.path.join(current_app.root_path, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    saved_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}{file_ext}")
    file.save(saved_path)
    
    # vừa thrrm vào
    
    try:
        chapter_titles = extract_chapters_from_file(saved_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # num_chapters = len(chapter_titles)
    # if num_chapters == 0:
    #     return jsonify({'error': 'Không tìm thấy chương trong tài liệu'}), 400
    
    
    
    # kết thúc

    # Tạo thư mục ảnh riêng
    image_dir = os.path.join(current_app.root_path, 'uploads', 'images', uuid.uuid4().hex)
    os.makedirs(image_dir, exist_ok=True)

    # Trích xuất chương
    if file_ext == ".pdf":
        chapters = extract_chapters_from_pdf_advance(saved_path, image_dir)
    elif file_ext == ".docx":
        chapters = extract_chapters_from_docx(saved_path, image_dir)
    else:
        return jsonify({'error': 'Chỉ hỗ trợ file .pdf và .docx'}), 400
    #print("in ra chapter", chapters)
    #return "đã chạy qua đoạn trích xuất file"
    num_chapters = len(chapters)
    if num_chapters == 0:
        return jsonify({'error': 'Không tìm thấy chương nào trong tài liệu.'}), 400

    print(f"✅ Tổng số chương trích xuất: {num_chapters}")

    # Sinh câu hỏi theo chương
    mcq_counts = distribute_counts(18, num_chapters)
    tf_counts = distribute_counts(4, num_chapters)
    short_counts = distribute_counts(6, num_chapters)
    
    print("in ra số lương câu của mcq", mcq_counts)
    print("in ra số lương câu của tf", tf_counts)
    print("in ra số lượng câu cảu short", short_counts)
    
    

    all_mcq, all_tf, all_short = [], [], []
    
    

    for i, chapter in enumerate(chapters):
        print("in ra i", i)
        #return "đã chạy trước các hàm gọi AI"
        text = chapter.get('text', '')
        #print("in ra text trong vòng lặp", text)
        title = chapter.get('title', f'Chương {i+1}')
        
        #  NẾU SAI THÌ MỞ LẠI ĐOẠN NÀY
        # if i < 4:
        #     tf_with_images = generate_tf_with_images([chapter], max_img=1)
        #     for tf_q in tf_with_images:
        #         tf_q['chapter'] = title
        #         all_tf.append(tf_q)
        # MỞ LẠI ĐOẠN NÀY
        
        
        # ĐOẠN SỬA LÀ ĐOẠN NÀY:::
        
        if i < 4:
            images = chapter.get("images", [])
            if images:
                tf_with_images = generate_tf_with_images([chapter], max_img=1)
                for tf_q in tf_with_images:
                    tf_q['chapter'] = title
                    if 'image_path' in tf_q:
                        tf_q['image_path'] = to_web_path(tf_q['image_path'])  # 🔧 CHUẨN HÓA
                    all_tf.append(tf_q)
            else:
                print(f"📄 Chương {i+1} không có ảnh, fallback sang sinh TF từ text")
                fallback_tf = generate_true_false_questions(text, num_questions=1)  # count=1 cho mỗi chương
                for tf_q in fallback_tf:
                    tf_q['chapter'] = title
                    tf_q['image_path'] = None  # Cho đồng nhất format
                    all_tf.append(tf_q)

        # if i < 4:
        #     tf_with_images = generate_tf_with_images([chapter], max_img=1)
        #     for tf_q in tf_with_images:
        #         tf_q['chapter'] = title
        #         all_tf.append(tf_q)
        
        
        # KẾT THÚC ĐOẠN SỬA!!!!!!
                

        mcqs = generate_mcq_questions(text, mcq_counts[i])
        for q in mcqs:
            q['chapter'] = title
            all_mcq.append(q)
            #print("in ra tổng số câu của mcq", all_mcq)

        shorts = generate_short_answer_questions(text, short_counts[i])
        for q in shorts:
            q['chapter'] = title
            all_short.append(q)
            #print(" in ra tổng số câu của short", all_short)
            
    print("in ra tổng số câu của tf", all_tf)
    print("in ra tổng số câu của mcq", all_mcq)
    print(" in ra tổng số câu của short", all_short)
            
            
    #return "đã chạy tới trước các hàm lưu"

    # Tạo exam_set
    user_id = current_user.id
    set_id = create_exam_set("Bộ đề mặc định", user_id)

    # Lưu vào DB
    save_mcq_questions(all_mcq, set_id, user_id)
    save_tf_questions(all_tf, set_id)
    save_short_answer_questions(all_short, set_id)

    # Chuyển sang trang sửa đề
    return redirect(url_for('highschool.edit_exam_set_view', exam_set_id=set_id))
#    
@highschool_bp.route('/edit_exam_set/<int:exam_set_id>')
@login_required
def edit_exam_set_view(exam_set_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy câu hỏi MCQ
    cursor.execute("""
        SELECT id, question_text, answer_a, answer_b, answer_c, answer_d, correct_answer
        FROM questions
        WHERE exam_set_id = %s
    """, (exam_set_id,))
    mcq_questions = cursor.fetchall()

    # Lấy câu hỏi Đúng/Sai
    cursor.execute("""
    SELECT 
        tf.id AS tf_question_id,
        tf.question_text,
        tf.image_url,
        tf.explanation,
        tfi.id AS item_id,
        tfi.statement_text,
        tfi.is_true,
        tfi.sort_order
    FROM tf_questions tf
    JOIN tf_items tfi ON tf.id = tfi.tf_question_id
    WHERE tf.exam_set_id = %s
    ORDER BY tf.id, tfi.sort_order
""", (exam_set_id,))
    tf_raw_data = cursor.fetchall()
    tf_questions = {}
    grouped_items = defaultdict(list)

# Gom mệnh đề theo câu hỏi
    for row in tf_raw_data:
        q_id = row['tf_question_id']
    
        if q_id not in tf_questions:
            tf_questions[q_id] = {
            'id': q_id,
            'question_text': row['question_text'],
            'image_url': row['image_url'],
            'explanation': row['explanation'],
            'items': []
        }

        tf_questions[q_id]['items'].append({
        'id': row['item_id'],
        'statement_text': row['statement_text'],
        'is_true': row['is_true'],
        'sort_order': row['sort_order']
    })

# Chuyển thành danh sách để dễ xử lý trong template
    tf_questions = list(tf_questions.values())
    #print("in ra danh sách tf_question", tf_questions)


    # Lấy câu hỏi trả lời ngắn
    cursor.execute("""
        SELECT id, question_text, correct_answer
        FROM short_answer_questions
        WHERE exam_set_id = %s
    """, (exam_set_id,))
    short_questions = cursor.fetchall()

    cursor.close()

    return render_template(
        'hsq_edit.html',
        exam_set_id=exam_set_id,
        mcq_questions=mcq_questions,
        tf_questions=tf_questions,
        short_questions=short_questions
    )
    #return f"Tạo đề thành công! (ID bộ đề: {exam_set_id})"
@highschool_bp.route("/shuffle_exam/<int:exam_set_id>", methods=["POST"])
def shuffle_exam(exam_set_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Lấy câu hỏi MCQ, True/False, Short Answer theo bộ đề
        cursor.execute("SELECT * FROM questions WHERE exam_set_id = %s", (exam_set_id,))
        mcq_questions = cursor.fetchall()

        cursor.execute("""
            SELECT tf.id, tf.question_text, tf.image_url, tf.exam_set_id, 
                    s.statement_text, s.is_true
            FROM tf_questions tf
            JOIN tf_items s ON s.tf_question_id = tf.id
            WHERE tf.exam_set_id = %s
        """, (exam_set_id,))
        tf_rows = cursor.fetchall()

        cursor.execute("SELECT * FROM short_answer_questions WHERE exam_set_id = %s", (exam_set_id,))
        short_answers = cursor.fetchall()

        # 2. Gom nhóm các câu TF theo ID
        tf_grouped = {}
        for row in tf_rows:
            qid = row['id']
            if qid not in tf_grouped:
                tf_grouped[qid] = {
                    'question_text': row['question_text'],
                    'image': row['image_url'],
        
                    'statements': []
                }
            tf_grouped[qid]['statements'].append({
                
                'content': row['statement_text'],
                'is_true': row['is_true']
            })

        # 3. Tạo 4 mã đề: 001–004, ví dụ 45-001, 45-002
        base_code = str(exam_set_id)
        versions = [f"{base_code}-00{i}" for i in range(1, 5)]

        for code in versions:
            # Lưu mã đề vào exam_codes nếu chưa có
            cursor.execute("SELECT COUNT(*) AS count FROM exam_codes WHERE code = %s", (code,))
            if cursor.fetchone()['count'] == 0:
                cursor.execute("INSERT INTO exam_codes (code, exam_set_id) VALUES (%s, %s)", (code, exam_set_id))
                conn.commit()
            cursor.execute("SELECT id FROM exam_codes WHERE code = %s", (code,))
            print(f"Exam code '{code}' -> exam_code_id: {row['id'] if row else 'not found'}")
            exam_code_id = cursor.fetchone()['id']

            # -- Xử lý MCQ --
            # Tráo vị trí câu hỏi
            shuffled_mcq = random.sample(mcq_questions, len(mcq_questions))
            for idx, q in enumerate(shuffled_mcq):
                # Tráo vị trí đáp án trong câu hỏi
                answers = [
                    ('A', q['answer_a']),
                    ('B', q['answer_b']),
                    ('C', q['answer_c']),
                    ('D', q['answer_d']),
                ]
                random.shuffle(answers)

                # Xác định đáp án đúng mới (theo label)
                correct_answer_text = q[f"answer_{q['correct_answer'].lower()}"]
                for new_label, ans_text in answers:
                    if ans_text == correct_answer_text:
                        new_correct_answer = new_label
                        break
                    
                print(f"Inserting question type MCQ with exam_code_id={exam_code_id}, question_id={q['id']}, position={idx + 1}")


                # Lưu vào exam_question_map
                cursor.execute("""
                    INSERT INTO exam_question_map
                    (exam_code_id, question_id, question_order, answer_a, answer_b, answer_c, answer_d, correct_answer, chapter, difficulty)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    exam_code_id,
                    q['id'],
                    idx + 1,
                    answers[0][1],
                    answers[1][1],
                    answers[2][1],
                    answers[3][1],
                    new_correct_answer,
                    q.get('chapter', None),
                    q.get('difficulty', None)
                ))

            # -- Xử lý True/False --
            shuffled_tf_keys = random.sample(list(tf_grouped.keys()), len(tf_grouped))
            for idx, tf_id in enumerate(shuffled_tf_keys):
                q = tf_grouped[tf_id]
                cursor.execute("""
                    INSERT INTO hs_question_map (exam_code_id, question_type, original_question_id, position)
                    VALUES (%s, 'TF', %s, %s)
                """, (exam_code_id, tf_id, idx + 1))
                hs_map_id = cursor.lastrowid

                # Tráo mệnh đề con
                statements = q['statements']
                random.shuffle(statements)
                labels = ['A', 'B', 'C', 'D']
                for pos, stmt in enumerate(statements, 1):
                    cursor.execute("""
                        INSERT INTO hs_tf_statements (hs_map_id, label, content, is_true, position)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (hs_map_id, labels[pos - 1], stmt['content'], stmt['is_true'], pos))

            # -- Xử lý Short Answer --
            shuffled_sa = random.sample(short_answers, len(short_answers))
            for idx, q in enumerate(shuffled_sa):
                cursor.execute("""
                    INSERT INTO hs_question_map (exam_code_id, question_type, original_question_id, position)
                    VALUES (%s, 'SA', %s, %s)
                """, (exam_code_id, q['id'], idx + 1))

            conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"success": True, "message": "Đã trộn thành công 4 mã đề."})

    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi khi trộn đề: {str(e)}"}), 500


