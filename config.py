import os
from dotenv import load_dotenv

load_dotenv()

FLASK_ENV = os.environ.get('FLASK_ENV', 'development')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    if not SECRET_KEY:
        if FLASK_ENV == 'production':
            # В проде без SECRET_KEY в окружении лучше упасть сразу,
            # чем молча подписывать сессии предсказуемым ключом.
            raise RuntimeError(
                'SECRET_KEY не задан в окружении. Создайте .env на основе '
                '.env.example и укажите случайный SECRET_KEY.'
            )
        # Для локальной разработки — предсказуемый, но явно помеченный ключ.
        SECRET_KEY = 'dev-only-insecure-key'