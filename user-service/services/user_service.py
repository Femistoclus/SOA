from models.user import User, UserProfile, db
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from kafka import KafkaProducer
import json
from datetime import datetime

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)


class UserService:
    """
    Класс, реализующий логику работы с базой данных сервиса пользователей.
    """

    @staticmethod
    def create_user(username, email, password, phone_number=None):
        """
        Ручка для создания нового пользователя. Нового пользователя можно создать, только если
        не существовало ранее пользователя с таким юзернемом и/или такой почтой (т.к. они отмечены в базе UNIQUE –
        при попытке создания получим ошибку IntegrityError).
        """
        try:
            user = User(username=username, email=email, phone_number=phone_number)
            user.set_password(password)

            profile = UserProfile(user=user)

            db.session.add(user)
            db.session.add(profile)
            db.session.commit()

            event = {
                'event_type': 'user_registered',
                'user_id': user.id,
                'username': user.username,
                'registration_date': datetime.now().isoformat()
            }
            producer.send('user-events', event)

            return user
        except IntegrityError:
            db.session.rollback()

            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return {"error": "Username already exists"}

            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                return {"error": "Email already exists"}

            return {"error": "Failed to create user"}

    @staticmethod
    def get_user_by_username(username):
        """Получение пользователя из БД по юзернейму"""
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_user_by_id(user_id):
        """Получение пользователя из БД по ID"""
        return User.query.get(user_id)

    @staticmethod
    def update_profile(user_id, profile_data):
        """Обновления профиля юзера"""
        user = User.query.get(user_id)
        if not user:
            return None

        if (
            "email" in profile_data
            and profile_data["email"]
            and profile_data["email"] != user.email
        ):
            existing_email = User.query.filter(
                User.id != user_id, User.email == profile_data["email"]
            ).first()
            if existing_email:
                return {"error": "Email already exists"}

        if "email" in profile_data and profile_data["email"]:
            user.email = profile_data["email"]
        if "phone_number" in profile_data:
            user.phone_number = profile_data["phone_number"]

        if not user.profile:
            user.profile = UserProfile(user_id=user_id)

        if "first_name" in profile_data:
            user.profile.first_name = profile_data["first_name"]
        if "last_name" in profile_data:
            user.profile.last_name = profile_data["last_name"]
        if "birthdate" in profile_data:
            user.profile.birthdate = profile_data["birthdate"]
        if "bio" in profile_data:
            user.profile.bio = profile_data["bio"]
        if "location" in profile_data:
            user.profile.location = profile_data["location"]

        user.updated_at = datetime.now()
        user.profile.updated_at = datetime.now()

        try:
            db.session.commit()
            return user
        except IntegrityError:
            db.session.rollback()
            if "email" in profile_data and profile_data["email"]:
                existing_email = User.query.filter(
                    User.id != user_id, User.email == profile_data["email"]
                ).first()
                if existing_email:
                    return {"error": "Email already exists"}

            return {"error": "Failed to update profile"}
