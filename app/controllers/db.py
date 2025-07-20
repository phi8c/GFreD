# db.py

import os
import mysql.connector
from dotenv import load_dotenv
load_dotenv()


# def get_db_connection():
#     conn = mysql.connector.connect(
#         host="localhost",
#         user="root",       # Thay bằng user MySQL của bạn
#         password="",       # Thay bằng password của bạn
#         database="everest" # Đặt tên database
#     )
#     return conn

def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "quizgenai")
    )
    return conn
    
