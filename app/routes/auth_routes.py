from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from controllers.db_users import get_user_by_email, create_user
from models.user_model import User
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/home')
def home():
    return render_template('home.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        existing_user = get_user_by_email(email)
        if existing_user:
            flash("Email đã được sử dụng.")
            return redirect(url_for('auth.register'))
        
        create_user(username, email, password)
        flash("Đăng ký thành công! Vui lòng đăng nhập.")
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_dict = get_user_by_email(email)

        if user_dict and check_password_hash(user_dict['password'], password):
            login_user(User(user_dict))
            return redirect(url_for('question.index'))

        flash("Email hoặc mật khẩu không đúng.")
        return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.home'))



