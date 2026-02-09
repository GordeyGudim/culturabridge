from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from config import Config
from models import db, User, Meeting
from auth import AuthService, AuthValidator
from datetime import datetime
import json

app = Flask(__name__)
app.config.from_object(Config)

# Инициализация базы данных
db.init_app(app)

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Создание таблиц при первом запуске
with app.app_context():
    db.create_all()

# Маршруты аутентификации
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        user, message = AuthService.authenticate_user(username, password)
        
        if user:
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Вход выполнен успешно!', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash(message, 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        form_data = {
            'username': request.form.get('username'),
            'email': request.form.get('email'),
            'password': request.form.get('password'),
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'age': request.form.get('age'),
            'country': request.form.get('country'),
            'native_language': request.form.get('native_language'),
            'learning_languages': request.form.getlist('learning_languages'),
            'interests': request.form.get('interests')
        }
        
        success, message = AuthService.register_user(form_data)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'danger')
    
    # Списки для выбора
    countries = ['Россия', 'США', 'Великобритания', 'Германия', 'Франция', 'Испания', 'Китай', 'Япония', 'Корея', 'Бразилия']
    languages = ['Английский', 'Испанский', 'Французский', 'Немецкий', 'Китайский', 'Японский', 'Корейский', 'Русский', 'Португальский', 'Итальянский']
    
    return render_template('register.html', countries=countries, languages=languages)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

# Личный кабинет
@app.route('/dashboard')
@login_required
def dashboard():
    # Получаем предстоящие встречи пользователя
    upcoming_meetings = Meeting.query.join(
        Meeting.participants
    ).filter(
        Meeting.scheduled_time > datetime.utcnow(),
        Meeting.is_active == True
    ).all()
    
    # Получаем рекомендации встреч
    recommended_meetings = Meeting.query.filter(
        Meeting.language.in_(current_user.learning_languages.split(',')),
        Meeting.scheduled_time > datetime.utcnow(),
        Meeting.is_active == True
    ).limit(5).all()
    
    user_data = {
        'username': current_user.username,
        'name': f"{current_user.first_name} {current_user.last_name}",
        'age': current_user.age,
        'country': current_user.country,
        'native_language': current_user.native_language,
        'learning_languages': current_user.learning_languages.split(',')
    }
    months_ru = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }
    
    from datetime import datetime
    now = datetime.now()
    current_date = f"{now.day} {months_ru[now.month]} {now.year}"
    
    return render_template('dashboard.html', 
                         user=user_data,
                         upcoming_meetings=upcoming_meetings,
                         recommended_meetings=recommended_meetings,
                         current_date=current_date)  # ДОБАВЬТЕ ЭТО!

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Обновление профиля
        current_user.first_name = request.form.get('first_name', current_user.first_name)
        current_user.last_name = request.form.get('last_name', current_user.last_name)
        current_user.country = request.form.get('country', current_user.country)
        current_user.interests = request.form.get('interests', current_user.interests)
        
        # Обновление языков
        new_languages = request.form.getlist('learning_languages')
        current_user.learning_languages = ','.join(new_languages)
        
        try:
            db.session.commit()
            flash('Профиль успешно обновлен!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении профиля: {str(e)}', 'danger')
    
    return render_template('profile.html', user=current_user)

# API для проверки доступности имени пользователя
@app.route('/api/check-username')
def check_username():
    username = request.args.get('username', '')
    exists = User.query.filter_by(username=username).first() is not None
    return jsonify({'available': not exists})

# API для проверки email
@app.route('/api/check-email')
def check_email():
    email = request.args.get('email', '')
    exists = User.query.filter_by(email=email).first() is not None
    
    # Проверка формата email
    is_valid = AuthValidator.validate_email(email)
    
    return jsonify({
        'available': not exists,
        'valid': is_valid
    })

# API для получения встреч
@app.route('/api/meetings')
@login_required
def get_meetings():
    topic = request.args.get('topic')
    language = request.args.get('language')
    level = request.args.get('level')
    
    query = Meeting.query.filter(
        Meeting.scheduled_time > datetime.utcnow(),
        Meeting.is_active == True
    )
    
    if topic:
        query = query.filter(Meeting.topic.contains(topic))
    if language:
        query = query.filter(Meeting.language == language)
    if level:
        query = query.filter(Meeting.level == level)
    
    meetings = query.limit(20).all()
    
    result = []
    for meeting in meetings:
        result.append({
            'id': meeting.id,
            'title': meeting.title,
            'topic': meeting.topic,
            'language': meeting.language,
            'level': meeting.level,
            'scheduled_time': meeting.scheduled_time.isoformat(),
            'participant_count': len(meeting.participants),
            'max_participants': meeting.max_participants
        })
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)