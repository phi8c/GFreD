from werkzeug.security import generate_password_hash, check_password_hash
from controllers.db import get_db_connection

# Lấy user theo email (dùng cho login)
def get_user_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM users WHERE email = %s"
    cursor.execute(query, (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# Lấy user theo id (dùng cho Flask-Login)
def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# Tạo user mới (dùng cho đăng ký)
def create_user(username, email, password):
    hashed_password = generate_password_hash(password)
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO users (username, email, password)
        VALUES (%s, %s, %s)
    """
    cursor.execute(query, (username, email, hashed_password))
    conn.commit()
    cursor.close()
    conn.close()