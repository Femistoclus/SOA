import pytest
from unittest.mock import patch, MagicMock
from services.user_service import UserService
from tests.mocks.db import mock_user, mock_db, MockUser, MockUserProfile
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def mock_session():
    return mock_db.session


def test_create_user_success(mock_session):
    username = "newuser"
    email = "new@example.com"
    password = "Password123"

    with patch("services.user_service.User", MockUser), patch(
        "services.user_service.UserProfile", MockUserProfile
    ), patch("services.user_service.db", mock_db):

        user = UserService.create_user(username, email, password)

        assert user is not None
        assert mock_session.added_objects
        assert mock_session.committed


def test_create_user_duplicate_username(mock_session):
    username = "existinguser"
    email = "new@example.com"
    password = "Password123"

    with patch("services.user_service.User", MockUser), patch(
        "services.user_service.UserProfile", MockUserProfile
    ), patch("services.user_service.db", mock_db), patch(
        "services.user_service.User.query.filter_by"
    ) as mock_filter_by:
        mock_db.session.commit = MagicMock(side_effect=IntegrityError("", "", ""))
        mock_filter_by.return_value.first.return_value = mock_user

        result = UserService.create_user(username, email, password)

        assert isinstance(result, dict)
        assert "error" in result
        assert "Username already exists" in result["error"]
        assert mock_session.rolled_back


def test_create_user_duplicate_email(mock_session):
    username = "newuser"
    email = "existing@example.com"
    password = "Password123"

    with patch("services.user_service.User", MockUser), patch(
        "services.user_service.UserProfile", MockUserProfile
    ), patch("services.user_service.db", mock_db), patch(
        "services.user_service.User.query.filter_by"
    ) as mock_filter_by:
        mock_db.session.commit = MagicMock(side_effect=IntegrityError("", "", ""))

        mock_filter_by.return_value.first.side_effect = [None, mock_user]

        result = UserService.create_user(username, email, password)

        assert isinstance(result, dict)
        assert "error" in result
        assert "Email already exists" in result["error"]
        assert mock_session.rolled_back


def test_get_user_by_username():
    username = "testuser"

    with patch("services.user_service.User", MockUser), patch(
        "services.user_service.User.query.filter_by"
    ) as mock_filter_by:
        mock_filter_by.return_value.first.return_value = mock_user

        user = UserService.get_user_by_username(username)

        assert user is mock_user
        mock_filter_by.assert_called_once_with(username=username)


def test_get_user_by_id():
    user_id = 1

    with patch("services.user_service.User", MockUser), patch(
        "services.user_service.User.query.get"
    ) as mock_get:

        mock_get.return_value = mock_user

        user = UserService.get_user_by_id(user_id)

        assert user is mock_user
        mock_get.assert_called_once_with(user_id)


def test_update_profile_success(mock_session):
    user_id = 1
    profile_data = {
        "first_name": "Updated",
        "last_name": "User",
        "email": "updated@example.com",
        "phone_number": "+19876543210",
    }

    with patch("services.user_service.User", MockUser), patch(
        "services.user_service.UserProfile", MockUserProfile
    ), patch("services.user_service.db", mock_db), patch(
        "services.user_service.User.query.get"
    ) as mock_get, patch(
        "services.user_service.User.query.filter"
    ) as mock_filter:

        mock_get.return_value = mock_user

        mock_filter_result = MagicMock()
        mock_filter_result.first.return_value = None
        mock_filter.return_value = mock_filter_result

        mock_db.session.commit = MagicMock()

        result = UserService.update_profile(user_id, profile_data)

        assert result is mock_user
        assert mock_user.email == "updated@example.com"
        assert mock_user.phone_number == "+19876543210"
        assert mock_user.profile.first_name == "Updated"
        assert mock_user.profile.last_name == "User"
        assert mock_session.committed


def test_update_profile_user_not_found():
    user_id = 999
    profile_data = {"first_name": "Updated"}

    with patch("services.user_service.User", MockUser), patch(
        "services.user_service.User.query.get"
    ) as mock_get:
        mock_get.return_value = None

        result = UserService.update_profile(user_id, profile_data)

        assert result is None
        mock_get.assert_called_once_with(user_id)


def test_update_profile_success_no_email_conflict(mock_session):
    user_id = 1
    profile_data = {
        "first_name": "Updated",
        "last_name": "User",
        # Не меняем email, чтобы избежать проверки на дубликат
        "phone_number": "+19876543210",
    }

    with patch("services.user_service.User", MockUser), patch(
        "services.user_service.UserProfile", MockUserProfile
    ), patch("services.user_service.db", mock_db), patch(
        "services.user_service.User.query.get"
    ) as mock_get:
        mock_get.return_value = mock_user

        result = UserService.update_profile(user_id, profile_data)

        assert result is mock_user
        assert mock_user.profile.first_name == "Updated"
        assert mock_user.profile.last_name == "User"
        assert mock_user.phone_number == "+19876543210"
        assert mock_session.committed


def test_update_profile_email_already_exists(mock_session):
    user_id = 1
    profile_data = {"email": "duplicate@example.com"}

    with patch("services.user_service.User", MockUser), patch(
        "services.user_service.UserProfile", MockUserProfile
    ), patch("services.user_service.db", mock_db), patch(
        "services.user_service.User.query.get"
    ) as mock_get, patch(
        "services.user_service.User.query.filter"
    ) as mock_filter:

        mock_get.return_value = mock_user

        duplicate_user = MagicMock()
        duplicate_user.id = 2
        mock_filter_result = MagicMock()
        mock_filter_result.first.return_value = duplicate_user
        mock_filter.return_value = mock_filter_result

        result = UserService.update_profile(user_id, profile_data)

        assert isinstance(result, dict)
        assert "error" in result
        assert "Email already exists" in result["error"]


def test_update_profile_create_missing_profile(mock_session):
    user_id = 1
    profile_data = {"first_name": "New"}

    user_without_profile = MagicMock()
    user_without_profile.id = user_id
    user_without_profile.profile = None

    with patch("services.user_service.User", MockUser), patch(
        "services.user_service.UserProfile", MockUserProfile
    ), patch("services.user_service.db", mock_db), patch(
        "services.user_service.User.query.get"
    ) as mock_get:
        mock_get.return_value = user_without_profile

        result = UserService.update_profile(user_id, profile_data)

        assert result is user_without_profile
        assert user_without_profile.profile is not None
        assert user_without_profile.profile.first_name == "New"
        assert mock_session.committed
