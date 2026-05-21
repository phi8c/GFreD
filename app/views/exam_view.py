# app/views/exam_view.py

from flask import Blueprint, jsonify
from controllers.exam_controller import shuffle_exam_versions, shuffle_advanced_exam_versions
from flask import render_template, request, redirect, url_for
from models.exam_model import check_exam_type 


# exam_bp = Blueprint('exam_bp', __name__)
# @exam_bp.route('/exam-ui')
# def exam_ui():
#     return render_template('generate_exam.html')

# @exam_bp.route('/generate-exams', methods=['POST'])
# def generate_exams():
#     try:
#         shuffle_exam_versions(num_versions=4)
#         return jsonify({"status": "success", "message": "Tạo 4 mã đề thành công."})
#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)})
exam_bp = Blueprint('exam_bp', __name__)

@exam_bp.route('/exam-ui')
def exam_ui():
    return render_template('generate_exam.html')

@exam_bp.route('/generate-exams', methods=['POST'])
def generate_exams():
    try:
        user_id = request.form.get('user_id')
        exam_set_id = request.form.get('exam_set_id')
        num_versions = int(request.form.get('num_versions', 4))  # default 4 nếu không truyền
        print("nhận được số lượng mã đề cần tạo", num_versions)
        
        
        
        

        if not user_id or not exam_set_id:
            return jsonify({"status": "error", "message": "Thiếu user_id hoặc exam_set_id!"})
        
        

        user_id = int(user_id)
        exam_set_id = int(exam_set_id)

        # Xác định bộ đề là basic hay advanced
        exam_type = check_exam_type(exam_set_id)

        if exam_type == "basic":
            shuffle_exam_versions(user_id, exam_set_id, num_versions)
            #return redirect(url_for('question.view_exam_set', exam_set_id=exam_set_id))
        else:  # advanced
            shuffle_advanced_exam_versions(user_id, exam_set_id, num_versions)
            #return redirect(url_for('question.view_exam_set', exam_set_id=exam_set_id))
        return jsonify({"status": "success", "redirect_url": url_for('question.view_exam_set', exam_set_id=exam_set_id)})


        #return jsonify({"status": "success", "message": f"Tạo {num_versions} mã đề thành công."})
           
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
