from flask import current_app
from models import db, User
from datetime import datetime
import re

class AuthValidator:
    @staticmethod
    def validate_email(email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username):
        if len(username) < 3 or len(username) > 50:
            return False, "Имя пользователя должно быть от 3 до 50 символов"
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Имя пользователя может содержать только буквы, цифры и подчеркивания"
        
        return True, ""
    
    @staticmethod
    def validate_password(password):
        if len(password) < 8:
            return False, "Пароль должен содержать минимум 8 символов"
        
        if not any(c.isupper() for c in password):
            return False, "Пароль должен содержать хотя бы одну заглавную букву"
        
        if not any(c.islower() for c in password):
            return False, "Пароль должен содержать хотя бы одну строчную букву"
        
        if not any(c.isdigit() for c in password):
            return False, "Пароль должен содержать хотя бы одну цифру"
        
        return True, ""
    
    @staticmethod
    def validate_age(age):
        try:
            age_int = int(age)
            if age_int < 13 or age_int > 19:
                return False, "Возраст должен быть от 13 до 19 лет"
            return True, ""
        except ValueError:
            return False, "Возраст должен быть числом"

class AuthService:
    @staticmethod
    def register_user(form_data):
        # Валидация данных
        if not AuthValidator.validate_email(form_data['email']):
            return False, "Некорректный email адрес"
        
        valid, msg = AuthValidator.validate_username(form_data['username'])
        if not valid:
            return False, msg
        
        valid, msg = AuthValidator.validate_password(form_data['password'])
        if not valid:
            return False, msg
        
        valid, msg = AuthValidator.validate_age(form_data['age'])
        if not valid:
            return False, msg
        
        # Проверка уникальности
        if User.query.filter_by(username=form_data['username']).first():
            return False, "Имя пользователя уже занято"
        
        if User.query.filter_by(email=form_data['email']).first():
            return False, "Email уже зарегистрирован"
        
        # Создание пользователя
        user = User(
            username=form_data['username'],
            email=form_data['email'],
            first_name=form_data['first_name'],
            last_name=form_data['last_name'],
            age=int(form_data['age']),
            country=form_data['country'],
            native_language=form_data['native_language'],
            learning_languages=','.join(form_data.get('learning_languages', [])),
            interests=form_data.get('interests', '')
        )
        
        user.set_password(form_data['password'])
        
        try:
            db.session.add(user)
            db.session.commit()
            return True, "Регистрация успешна! Теперь войдите в систему."
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при регистрации: {str(e)}"
    
    @staticmethod
    def authenticate_user(username, password):
        user = User.query.filter_by(username=username).first()
        
        if not user:
            user = User.query.filter_by(email=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                return None, "Аккаунт деактивирован"
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            return user, "Успешный вход"
        
        return None, "Неверное имя пользователя или пароль"