from app import app, db
import models  # Импортируем модели

with app.app_context():
    db.drop_all()      # Удалить все таблицы
    db.create_all()    # Создать заново с новыми полями
    print("✅ База данных пересоздана с полем telemost_link!")