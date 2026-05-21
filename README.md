# Question

## Giới thiệu

Đây là một dự án web sinh đề thi trắc nghiệm, tự luận và quản lý phòng thi, chấm điểm thi được xây dựng bằng Python Flask. Ứng dụng hỗ trợ:

- Đăng ký / đăng nhập người dùng
- Tạo, chỉnh sửa và quản lý bộ đề thi
- Trích xuất chương từ file tài liệu
- Sinh câu hỏi và xuất đề thi
- Quản lý phòng thi, danh sách học sinh và xem kết quả
- Tích hợp Flask-SocketIO để xử lý realtime
- Gửi email qua Flask-Mail
- Kết nối MySQL để lưu trữ dữ liệu

## Cấu trúc chính của dự án

- `run.py`: điểm vào chính khi chạy server bằng `socketio.run(app, debug=True)`.
- `wsgi.py`: tạo app Flask để triển khai trên máy chủ WSGI.
- `app/__init__.py`: định nghĩa hàm `create_app()` và đăng ký các blueprint.
- `app/gen_questions.py`: blueprint chính xử lý upload file, trích xuất chương, tạo ngân hàng câu hỏi và sinh bộ đề.
- `app/controllers/`: chứa các controller xử lý dữ liệu, kết nối database và socket event.
- `app/models/`: chứa model dữ liệu, bao gồm `user_model.py`.
- `app/views/`, `app/routes/`: chứa các view và route HTML.
- `app/templates/`: chứa các file template Jinja2.
- `app/static/`: chứa CSS, JS, icon và tài nguyên frontend.
- `app/uploads/`: thư mục lưu file tải lên và file xuất.
- `requirements.txt`: danh sách dependency Python.

## Yêu cầu hệ thống

- Python 3.11+ (hoặc Python 3.10/3.12 nếu tương thích)
- MySQL server đang chạy
- `pip` để cài đặt các thư viện
- Quyền tạo thư mục `uploads` trong thư mục dự án

> Lưu ý: `requirements.txt` chứa nhiều thư viện AI/ML nặng như `transformers`, `sentence-transformers`, `spacy`, `torch`, `openai`.

## Cài đặt và chạy dự án

1. Mở terminal và chuyển tới thư mục dự án:

```bash
cd d:\QuestionGQuuuuuuX
```

2. Tạo môi trường ảo Python và kích hoạt:

```bash
python -m venv venv
venv\Scripts\activate
```

3. Cập nhật `pip` và cài đặt phụ thuộc:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

4. Tạo file cấu hình môi trường `.env` ở gốc dự án với nội dung tương tự:

```env
SECRET_KEY=your_secret_key
FLASK_ENV=development
OPENAI_API_KEY=your_openai_api_key
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=quizgenai
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_email_password
MAIL_DEFAULT_SENDER=your_email@gmail.com
```

5. Chuẩn bị MySQL database:

- Tạo database theo tên trong `MYSQL_DATABASE`.
- Tạo các bảng cần thiết như `users`, `exam_sets`, `questions`, `question_bank`, `exam_codes`, ... theo thiết kế ứng dụng.

> Dự án không cung cấp file migration schema, nên bạn cần tự tạo bảng dựa trên logic trong các controller và route.

6. Chạy ứng dụng:

```bash
python run.py
```

Mở trình duyệt và truy cập:

```text
http://localhost:5000
```

## Điểm quan trọng cần biết

- `run.py` dùng `eventlet` để chạy Socket.IO.
- `app/__init__.py` sử dụng `create_app()` và đăng ký các blueprint:
  - `question_bp`
  - `exam_bp`
  - `room_bp`
  - `student_bp`
  - `statistical_bp`
  - `highschool_bp`
  - `exam_hs_bp`
  - `auth_bp`
- `app/controllers/extensions.py` khai báo `socketio` và `mail`.
- `app/gen_questions.py` sử dụng `SentenceTransformer` để kiểm tra trùng lặp câu hỏi và xử lý tách chương.
- `config.py` đọc cấu hình từ `.env`.

## Chạy trên môi trường sản xuất

Nếu muốn triển khai bằng WSGI, bạn có thể dùng `wsgi.py` hoặc một server như Gunicorn:

```bash
gunicorn wsgi:app
```

Tuy nhiên với Socket.IO, nên giữ `run.py` và `eventlet` để đảm bảo realtime hoạt động đúng.

## Gợi ý sửa đổi nhanh

- Nếu cần thay đổi thư mục upload, chỉnh `app/__init__.py` tại `UPLOAD_FOLDER`.
- Nếu muốn vô hiệu `MAIL`, chỉnh `MAIL_*` trong `.env` hoặc `config.py`.
- Nếu muốn dùng `Flask-Login`, đăng ký user và bảng `users` phải đúng cấu trúc.

## Kết luận

Dự án này là một hệ thống tạo và quản lý đề thi online với nhiều tính năng: upload tệp, tách chương, tạo câu hỏi, lưu đề, quản lý phòng và gửi email. Để chạy đúng, bạn cần cài đặt môi trường Python, MySQL và điền các biến môi trường trong `.env`.
