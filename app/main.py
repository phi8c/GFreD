from flask import Flask, send_from_directory
from views.exam_view import exam_bp
from controllers.room_controller import room_bp
from controllers.student_exam_controller import student_bp
from controllers.statistical_room_controller import statistical_bp
from controllers.tp_question_hs import highschool_bp
from controllers.tp_exam_hs import exam_hs_bp
from flask import Flask, logging, request, render_template, jsonify
#from flask_socketio import SocketIO
from controllers.extensions import socketio, mail
import controllers.socket_events
from app import question_bp 
from flask_login import LoginManager, current_user, login_required
from models.user_model import User
from controllers.db_users import get_user_by_id



from routes.auth_routes import auth_bp  # <-- Blueprint
#from controllers.mail_event import init_mail  # 🔥 nhập ở đây



# @exam_bp.route('/exam-ui', methods=['GET'])
# def exam_ui():
#     return render_template('generate_exam.html')


app = Flask(__name__)
app.config.from_object('config')  # load từ file config.py
app.config['UPLOAD_FOLDER'] = 'uploads'
socketio.init_app(app)
app.register_blueprint(question_bp)  # <- Từ app.py
app.register_blueprint(exam_bp)
app.register_blueprint(room_bp)
app.register_blueprint(student_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(statistical_bp)
app.register_blueprint(highschool_bp)
app.register_blueprint(exam_hs_bp)
#socketio = SocketIO(app)



@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)




@app.after_request
def add_security_headers(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

#
#

# Khởi tạo LoginManager ở đây
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # tên endpoint, không phải tên file

# Cung cấp user loader
@login_manager.user_loader
def load_user(user_id):
    user_dict = get_user_by_id(user_id)
    return User(user_dict) if user_dict else None

#
#


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'phimklc1327@gmail.com'
app.config['MAIL_PASSWORD'] = 'dsdw vkrf jkqb kviw'
app.config['MAIL_DEFAULT_SENDER'] = 'phimklc1327@gmail.com'

# ✅ Khởi tạo mail sau khi app có config
mail.init_app(app)

#init_mail(app)  # ✅ cấu hình mail ở đây

#import controllers.socket_events  # nơi xử lý emit/receive

if __name__ == '__main__':
    print("🔥 Flask app running at http://localhost:5000")
    #app.run(debug=True)
    socketio.run(app, debug=True)
