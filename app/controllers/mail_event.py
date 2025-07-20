from flask_mail import Mail, Message
from flask import current_app

from controllers.extensions import mail



# def init_mail(app):
#     app.config['MAIL_SERVER'] = 'smtp.gmail.com'
#     app.config['MAIL_PORT'] = 587
#     app.config['MAIL_USE_TLS'] = True
#     app.config['MAIL_USERNAME'] = 'phimklc1327@gmail.com'
#     app.config['MAIL_PASSWORD'] = 'dsdw vkrf jkqb kviw'
#     app.config['MAIL_DEFAULT_SENDER'] = 'phimklc1327@gmail.com'
#     mail.init_app(app)

def send_otp_email(to_email, otp_code):
    with current_app.app_context():
        msg = Message('Mã OTP vào phòng thi', recipients=[to_email])
        msg.body = f'Mã OTP của bạn là: {otp_code}'
        mail.send(msg)
