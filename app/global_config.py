# app/global_config.py
import os

# Lấy đúng thư mục uploads vật lý
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
