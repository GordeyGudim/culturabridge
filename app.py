from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from config import Config
from models import db, User, Meeting, MeetingParticipant, MeetingRoom, RoomParticipant
from auth import AuthService, AuthValidator
from meeting_service import MeetingService
from datetime import datetime
import json

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    # Старая статистика
    total_meetings = MeetingParticipant.query.filter_by(user_id=current_user.id).count()
    total_friends = 0
    total_languages = len(current_user.learning_languages.split(',')) if current_user.learning_languages else 0
    total_hours = total_meetings * 1
    
    user_data = {
        'username': current_user.username,
        'name': f"{current_user.first_name} {current_user.last_name}",
        'age': current_user.age,
        'country': current_user.country,
        'native_language': current_user.native_language,
        'learning_languages': current_user.learning_languages.split(',') if current_user.learning_languages else [],
        'stats': {
            'total_meetings': total_meetings,
            'total_friends': total_friends,
            'total_languages': total_languages,
            'total_hours': total_hours
        }
    }
    
    # Текущая дата на русском
    months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    
    now = datetime.now()
    current_date = f"{now.day} {months_ru[now.month-1]} {now.year}"
    
    return render_template('dashboard.html', 
                         user=user_data,
                         current_date=current_date)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name', current_user.first_name)
        current_user.last_name = request.form.get('last_name', current_user.last_name)
        current_user.country = request.form.get('country', current_user.country)
        current_user.interests = request.form.get('interests', current_user.interests)
        
        new_languages = request.form.getlist('learning_languages')
        current_user.learning_languages = ','.join(new_languages)
        
        try:
            db.session.commit()
            flash('Профиль успешно обновлен!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении профиля: {str(e)}', 'danger')
    
    learning_languages_list = current_user.learning_languages.split(',') if current_user.learning_languages else []
    
    return render_template('profile.html', 
                         user=current_user, 
                         learning_languages_list=learning_languages_list)

# Система встреч
@app.route('/meetings/create', methods=['GET', 'POST'])
@login_required
def create_meeting():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        topic = request.form.get('topic')
        language = request.form.get('language')
        level = request.form.get('level')
        max_participants = int(request.form.get('max_participants', 6))
        
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        scheduled_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        
        room, message = MeetingService.create_room(
            user_id=current_user.id,
            title=title,
            description=description,
            topic=topic,
            language=language,
            level=level,
            scheduled_time=scheduled_time,
            max_participants=max_participants
        )
        
        if room:
            flash('Встреча успешно создана!', 'success')
            return redirect(url_for('meeting_detail', room_id=room.id))
        else:
            flash(message, 'danger')
    
    topics = ['🎮 Видеоигры', '🎵 K-pop и J-pop', '🎬 Фильмы и сериалы', 
              '📚 Литература', '🌍 Экология', '⚽ Спорт', '🍿 Культура питания',
              '💻 Технологии', '🎨 Искусство', '✈️ Путешествия']
    
    languages = ['Английский', 'Испанский', 'Французский', 'Немецкий', 
                 'Китайский', 'Японский', 'Корейский', 'Итальянский']
    
    levels = ['Начинающий', 'Средний', 'Продвинутый']
    
    return render_template('create_meeting.html', 
                         topics=topics, 
                         languages=languages, 
                         levels=levels)

@app.route('/meetings')
@login_required
def meetings_list():
    filters = {
        'topic': request.args.get('topic'),
        'language': request.args.get('language'),
        'level': request.args.get('level')
    }
    
    upcoming_meetings = MeetingService.get_upcoming_rooms(
        user_id=current_user.id,
        filters=filters
    )
    
    popular_topics = MeetingService.get_popular_topics()
    
    return render_template('meetings.html',
                         meetings=upcoming_meetings,
                         popular_topics=popular_topics,
                         filters=filters)

@app.route('/meetings/<int:room_id>')
@login_required
def meeting_detail(room_id):
    room = MeetingRoom.query.get_or_404(room_id)
    
    is_participant = RoomParticipant.query.filter_by(
        user_id=current_user.id,
        room_id=room_id
    ).first() is not None
    
    is_moderator = room.moderator_id == current_user.id
    
    participants = RoomParticipant.query.filter_by(room_id=room_id).all()
    
    return render_template('meeting_detail.html',
                         room=room,
                         is_participant=is_participant,
                         is_moderator=is_moderator,
                         participants=participants)

@app.route('/meetings/<int:room_id>/join', methods=['POST'])
@login_required
def join_meeting(room_id):
    success, message = MeetingService.join_room(current_user.id, room_id)
    
    if success:
        flash('Вы успешно присоединились к встрече!', 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('meeting_detail', room_id=room_id))

@app.route('/my-meetings')
@login_required
def my_meetings():
    upcoming = MeetingService.get_user_rooms(current_user.id)
    
    past_meetings = MeetingRoom.query.join(
        RoomParticipant
    ).filter(
        RoomParticipant.user_id == current_user.id,
        MeetingRoom.scheduled_time <= datetime.utcnow(),
        MeetingRoom.is_active == False
    ).order_by(
        MeetingRoom.scheduled_time.desc()
    ).all()
    
    return render_template('my_meetings.html',
                         upcoming_meetings=upcoming,
                         past_meetings=past_meetings)

# API эндпоинты
@app.route('/api/check-username')
def check_username():
    username = request.args.get('username', '')
    exists = User.query.filter_by(username=username).first() is not None
    return jsonify({'available': not exists})

@app.route('/api/check-email')
def check_email():
    email = request.args.get('email', '')
    exists = User.query.filter_by(email=email).first() is not None
    
    is_valid = AuthValidator.validate_email(email)
    
    return jsonify({
        'available': not exists,
        'valid': is_valid
    })

@app.route('/api/meetings')
@login_required
def get_meetings():
    topic = request.args.get('topic')
    language = request.args.get('language')
    level = request.args.get('level')
    
    query = MeetingRoom.query.filter(
        MeetingRoom.scheduled_time > datetime.utcnow(),
        MeetingRoom.is_active == True
    )
    
    if topic:
        query = query.filter(MeetingRoom.topic.contains(topic))
    if language:
        query = query.filter(MeetingRoom.language == language)
    if level:
        query = query.filter(MeetingRoom.level == level)
    
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
            'participant_count': meeting.current_participants,
            'max_participants': meeting.max_participants
        })
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)