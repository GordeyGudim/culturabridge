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
@app.route('/create_meeting', methods=['GET', 'POST'])
@login_required
def create_meeting():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        topic = request.form.get('topic')
        language = request.form.get('language')
        level = request.form.get('level')
        scheduled_time_str = request.form.get('scheduled_time')
        max_participants = request.form.get('max_participants', 6)
        
        if not all([title, topic, language, level, scheduled_time_str]):
            flash('Заполните все обязательные поля', 'danger')
            return render_template('create_meeting.html')
        
        try:
            from datetime import datetime
            scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%dT%H:%M')
            
            meeting = Meeting(
                title=title,
                description=description,
                topic=topic,
                language=language,
                level=level,
                moderator_id=current_user.id,
                scheduled_time=scheduled_time,
                max_participants=int(max_participants),
                is_active=True
            )
            
            db.session.add(meeting)
            db.session.commit()
            
            # Добавляем создателя как участника
            participant = MeetingParticipant(
                user_id=current_user.id,
                meeting_id=meeting.id
            )
            db.session.add(participant)
            db.session.commit()

            flash('Встреча успешно создана!', 'success')
            return redirect(url_for('meeting_detail', meeting_id=meeting.id))
            
        except ValueError as e:
            flash(f'Ошибка в формате даты: {str(e)}', 'danger')
            return render_template('create_meeting.html')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании встречи: {str(e)}', 'danger')
            return render_template('create_meeting.html')
    
    return render_template('create_meeting.html')
    
@app.route('/meetings')
@login_required
def meetings_list():
    # Получаем фильтры из URL
    filters = {
        'topic': request.args.get('topic'),
        'language': request.args.get('language'),
        'level': request.args.get('level')
    }
    
    # Базовый запрос для всех активных встреч
    query = Meeting.query.filter_by(is_active=True)
    
    # Применяем фильтры
    if filters['topic']:
        query = query.filter(Meeting.topic.ilike(f"%{filters['topic']}%"))
    
    if filters['language']:
        query = query.filter_by(language=filters['language'])
    
    if filters['level']:
        query = query.filter_by(level=filters['level'])
    
    # Сортируем по дате (ближайшие первые)
    upcoming_meetings = query.order_by(Meeting.scheduled_time.asc()).all()
    
    # Получаем популярные темы (если функция есть)
    try:
        popular_topics = MeetingService.get_popular_topics()
    except:
        # Если MeetingService не существует, получаем популярные темы напрямую
        popular_topics = db.session.query(
            Meeting.topic,
            db.func.count(Meeting.id).label('count')
        ).group_by(Meeting.topic)\
         .order_by(db.desc('count'))\
         .limit(10)\
         .all()
        popular_topics = [topic for topic, count in popular_topics]
    
    return render_template('meetings.html',
                         meetings=upcoming_meetings,
                         popular_topics=popular_topics,
                         filters=filters,
                         current_time=datetime.utcnow())

@app.route('/meeting/<int:meeting_id>')
@login_required
def meeting_detail(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    return render_template('meeting_detail.html', meeting=meeting)

@app.route('/meetings/<int:room_id>/join', methods=['POST'])
@login_required
def join_meeting(room_id):
    success, message = MeetingService.join_room(current_user.id, room_id)
    
    if success:
        flash('Вы успешно присоединились к встрече!', 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('meeting_detail', room_id=room_id))

@app.route('/my_meetings')
@login_required
def my_meetings():
    # Получаем встречи, где пользователь является участником
    # Через таблицу MeetingParticipant
    participant_meetings = Meeting.query\
        .join(MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id)\
        .filter(MeetingParticipant.user_id == current_user.id)\
        .order_by(Meeting.scheduled_time.asc())\
        .all()
    
    # Получаем встречи, где пользователь модератор
    moderated_meetings = Meeting.query\
        .filter(Meeting.moderator_id == current_user.id)\
        .order_by(Meeting.scheduled_time.asc())\
        .all()
    
    # Объединяем и убираем дубликаты
    all_meetings = participant_meetings + moderated_meetings
    unique_meetings = []
    seen_ids = set()
    
    for meeting in all_meetings:
        if meeting.id not in seen_ids:
            seen_ids.add(meeting.id)
            unique_meetings.append(meeting)
    
    return render_template('my_meetings.html', 
                         meetings=unique_meetings,
                         current_time=datetime.utcnow())

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