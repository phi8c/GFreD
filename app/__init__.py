from flask import Flask, send_from_directory
from flask_login import LoginManager
from flask_mail import Mail

import os

from config import Config
from app.models.user_model import User
from app.controllers.db_users import get_user_by_id
from app.controllers.extensions import socketio, mail



# # Blueprint imports
# from views.exam_view import exam_bp
# from controllers.room_controller import room_bp
# from controllers.student_exam_controller import student_bp
# from controllers.statistical_room_controller import statistical_bp
# from controllers.tp_question_hs import highschool_bp
# from controllers.tp_exam_hs import exam_hs_bp
# from routes.auth_routes import auth_bp
# from app import question_bp  # <-- Ensure this import is valid

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    #app.config['UPLOAD_FOLDER'] = 'uploads'
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # → thư mục /app
    UPLOAD_PATH = os.path.join(BASE_DIR, 'uploads')  # → app/uploads

    app.config['UPLOAD_FOLDER'] = UPLOAD_PATH  # dùng cho serve ảnh
    
    
    
    
    

# Blueprint imports
    from app.views.exam_view import exam_bp
    from app.controllers.room_controller import room_bp
    from app.controllers.student_exam_controller import student_bp
    from app.controllers.statistical_room_controller import statistical_bp
    from app.controllers.tp_question_hs import highschool_bp
    from app.controllers.tp_exam_hs import exam_hs_bp
    from app.routes.auth_routes import auth_bp
    from gen_questions import question_bp  # <-- Ensure this import is valid

    # Init extensions
    socketio.init_app(app)
    #app.config.from_object(Config)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register blueprints
    app.register_blueprint(question_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(room_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(statistical_bp)
    app.register_blueprint(highschool_bp)
    app.register_blueprint(exam_hs_bp)

    # Route serve file
    @app.route('/uploads/<path:filename>')
    def serve_uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        user_dict = get_user_by_id(user_id)
        return User(user_dict) if user_dict else None
    @app.after_request
    def add_security_headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    from app.controllers import socket_events


    return app, socketio
