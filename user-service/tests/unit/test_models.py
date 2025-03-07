from models.user import User
from flask_bcrypt import Bcrypt


def test_user_set_password():
    bcrypt = Bcrypt()
    user = User(username="testuser", email="test@example.com")

    user.set_password("password123")

    assert user.password_hash is not None
    assert user.password_hash != "password123"
    assert bcrypt.check_password_hash(user.password_hash, "password123")


def test_user_check_password():

    user = User(username="testuser", email="test@example.com")
    user.set_password("password123")

    assert user.check_password("password123") is True
    assert user.check_password("wrongpassword") is False
