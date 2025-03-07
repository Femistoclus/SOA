import pytest
import jwt
import datetime
from unittest.mock import patch

from app import create_app
from tests.mocks.db import mock_db, MockUser, mock_user, MockUserProfile, MockUserRole


@pytest.fixture
def app():
    with patch("models.user.db", mock_db), patch("models.user.User", MockUser), patch(
        "models.user.UserProfile", MockUserProfile
    ), patch("models.user.UserRole", MockUserRole):
        app = create_app()
        app.config.update(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "JWT_SECRET_KEY": "test-jwt-secret-key",
            }
        )
        with app.app_context():
            yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def token_header():
    token = jwt.encode(
        {"sub": 1, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
        "test-jwt-secret-key",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_user_service():
    with patch("routes.user_routes.UserService") as mock_service:
        mock_service.create_user.return_value = mock_user
        mock_service.get_user_by_username.return_value = mock_user
        mock_service.get_user_by_id.return_value = mock_user
        mock_service.update_profile.return_value = mock_user
        yield mock_service
