from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.username = user_dict['username']
        self.email = user_dict['email']
        self.password = user_dict['password']
        self.role = user_dict.get('role', 'user')

    def get_id(self):
        return str(self.id)
