from datetime import datetime, timedelta
from models import db, MeetingRoom, RoomParticipant, User, Meeting, MeetingParticipant

class MeetingService:
    
    @staticmethod
    def create_room(user_id, title, description, topic, language, level, 
                   scheduled_time, max_participants=6, duration=60):
        """Создание новой тематической комнаты"""
        
        user = User.query.get(user_id)
        if not user:
            return None, "Пользователь не найден"
        
        if user.age < 16:
            return None, "Только пользователи от 16 лет могут создавать комнаты"
        
        if scheduled_time <= datetime.utcnow():
            return None, "Время встречи должно быть в будущем"
        
        room = MeetingRoom(
            title=title,
            description=description,
            topic=topic,
            language=language,
            level=level,
            max_participants=max_participants,
            moderator_id=user_id,
            scheduled_time=scheduled_time,
            duration=duration,
            is_active=True
        )
        
        try:
            db.session.add(room)
            db.session.flush()
            
            participant = RoomParticipant(user_id=user_id, room_id=room.id)
            db.session.add(participant)
            room.current_participants += 1
            
            db.session.commit()
            return room, "Комната успешно создана"
        except Exception as e:
            db.session.rollback()
            return None, f"Ошибка при создании комнаты: {str(e)}"
    
    @staticmethod
    def join_room(user_id, room_id):
        """Присоединение пользователя к комнате"""
        
        room = MeetingRoom.query.get(room_id)
        if not room:
            return False, "Комната не найдена"
        
        if not room.is_active:
            return False, "Эта встреча уже завершена"
        
        if room.current_participants >= room.max_participants:
            return False, "Комната заполнена"
        
        if room.scheduled_time <= datetime.utcnow():
            return False, "Встреча уже началась или завершилась"
        
        existing = RoomParticipant.query.filter_by(
            user_id=user_id, 
            room_id=room_id
        ).first()
        
        if existing:
            return False, "Вы уже присоединились к этой встрече"
        
        try:
            participant = RoomParticipant(
                user_id=user_id,
                room_id=room_id
            )
            
            room.current_participants += 1
            
            db.session.add(participant)
            db.session.commit()
            
            return True, "Вы успешно присоединились к встрече"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при присоединении: {str(e)}"
    
    @staticmethod
    def get_upcoming_rooms(user_id=None, filters=None):
        """Получение предстоящих комнат"""
        
        query = MeetingRoom.query.filter(
            MeetingRoom.scheduled_time > datetime.utcnow(),
            MeetingRoom.is_active == True,
            MeetingRoom.current_participants < MeetingRoom.max_participants
        )
        
        if filters:
            if filters.get('topic'):
                query = query.filter(MeetingRoom.topic.contains(filters['topic']))
            if filters.get('language'):
                query = query.filter(MeetingRoom.language == filters['language'])
            if filters.get('level'):
                query = query.filter(MeetingRoom.level == filters['level'])
        
        if user_id:
            user_rooms = db.session.query(RoomParticipant.room_id).filter(
                RoomParticipant.user_id == user_id
            ).subquery()
            query = query.filter(~MeetingRoom.id.in_(user_rooms))
        
        query = query.order_by(MeetingRoom.scheduled_time.asc())
        return query.all()
    
    @staticmethod
    def get_user_rooms(user_id):
        """Получение комнат пользователя"""
        
        rooms = MeetingRoom.query.join(
            RoomParticipant
        ).filter(
            RoomParticipant.user_id == user_id,
            MeetingRoom.is_active == True
        ).order_by(
            MeetingRoom.scheduled_time.asc()
        ).all()
        
        return rooms
    
    @staticmethod
    def get_popular_topics():
        """Получение популярных тем"""
        
        from sqlalchemy import func
        
        try:
            popular = db.session.query(
                MeetingRoom.topic,
                func.count(MeetingRoom.id).label('count')
            ).filter(
                MeetingRoom.is_active == True,
                MeetingRoom.scheduled_time > datetime.utcnow()
            ).group_by(
                MeetingRoom.topic
            ).order_by(
                func.count(MeetingRoom.id).desc()
            ).limit(10).all()
            
            return [topic for topic, count in popular]
        except:
            return ['🎮 Видеоигры', '🎵 K-pop и J-pop', '🎬 Фильмы и сериалы', 
                   '🌍 Экология', '⚽ Спорт', '🍿 Культура питания']