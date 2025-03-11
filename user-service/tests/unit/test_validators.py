import pytest
from marshmallow import ValidationError
from datetime import datetime, timedelta
from utils.validators import RegisterSchema, LoginSchema, ProfileUpdateSchema


class TestRegisterSchema:

    def test_valid_data(self):
        data = {
            "username": "validuser",
            "email": "valid@mail.com",
            "password": "ValidPass123",
            "phone_number": "+12345678901",
        }
        errors = RegisterSchema().validate(data)
        assert not errors

    def test_invalid_username_too_short(self):
        data = {"username": "abc", "email": "u@ex.com", "password": "ValidPass123"}
        errors = RegisterSchema().validate(data)
        assert "username" in errors

    def test_invalid_username_chars(self):
        data = {"username": "bad#name", "email": "u@ex.com", "password": "ValidPass123"}
        errors = RegisterSchema().validate(data)
        assert "username" in errors

    def test_invalid_email_format(self):
        data = {
            "username": "validuser",
            "email": "invalidemail",
            "password": "Valid12345",
        }
        errors = RegisterSchema().validate(data)
        assert "email" in errors

    def test_invalid_password_no_digit(self):
        data = {
            "username": "validuser",
            "email": "valid@ex.com",
            "password": "WeakPassword",
        }
        errors = RegisterSchema().validate(data)
        assert "password" in errors

    def test_invalid_password_no_uppercase_letter(self):
        data = {
            "username": "validuser",
            "email": "valid@ex.com",
            "password": "no uppercase 12345",
        }
        errors = RegisterSchema().validate(data)
        assert "password" in errors

    def test_invalid_password_no_lowercase_letter(self):
        data = {
            "username": "validuser",
            "email": "valid@ex.com",
            "password": "NO LOWERCASE 12345",
        }
        errors = RegisterSchema().validate(data)
        assert "password" in errors

    def test_invalid_phone_format(self):
        data = {
            "username": "user",
            "email": "user@ex.com",
            "password": "Pass12345",
            "phone_number": "incorrect",
        }
        errors = RegisterSchema().validate(data)
        assert "phone_number" in errors


class TestLoginSchema:

    def test_login_valid(self):
        assert not LoginSchema().validate(
            {"username": "user", "password": "CorrectPass123"}
        )

    def test_login_no_username(self):
        errors = LoginSchema().validate({"password": "CorrectPass123"})
        assert "username" in errors

    def test_login_no_password(self):
        errors = LoginSchema().validate({"username": "user"})
        assert "password" in errors


class TestProfileUpdateSchema:

    def test_valid_update_all_fields(self):
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "birthdate": "1990-01-01",
            "bio": "Tester",
            "location": "US",
            "email": "new@example.com",
            "phone_number": "+1234567890",
        }
        errors = ProfileUpdateSchema().validate(data)
        assert not errors

    def test_invalid_email(self):
        data = {"email": "Wrong"}
        errors = ProfileUpdateSchema().validate(data)
        assert "email" in errors

    def test_future_birthdate(self):
        future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        data = {"birthdate": future_date}
        with pytest.raises(ValidationError):
            ProfileUpdateSchema().load(data)

    def test_invalid_phone_number_update(self):
        data = {"phone_number": "1234abc"}
        errors = ProfileUpdateSchema().validate(data)
        assert "phone_number" in errors

    def test_optional_profile_update_fields_all_empty(self):
        assert not ProfileUpdateSchema().validate(
            {"first_name": None, "last_name": None, "bio": None, "location": None}
        )


class TestRegisterSchemaEdgeCases:

    def test_empty_register_payload(self):
        errors = RegisterSchema().validate({})
        assert "username" in errors and "email" in errors and "password" in errors

    def test_phone_number_too_long(self):
        errors = RegisterSchema().validate(
            {
                "username": "user",
                "email": "u@mail.com",
                "password": "Valid1234",
                "phone_number": "+12345678901234567890",
            }
        )
        assert "phone_number" in errors

    def test_phone_number_too_short(self):
        assert RegisterSchema().validate(
            {
                "username": "user",
                "email": "u@mail.com",
                "password": "validPass123",
                "phone_number": "+123",
            }
        )["phone_number"]

    def test_password_too_short(self):
        assert RegisterSchema().validate(
            {
                "username": "user",
                "email": "u@mail.com",
                "password": "small",
                "phone_number": "+1234567890",
            }
        )["password"]

    def test_username_underscore_allowed(self):
        assert not RegisterSchema().validate(
            {"username": "user_name", "email": "u@mail.com", "password": "Valid12345"}
        )

    def test_username_other_specials_disallowed(self):
        assert RegisterSchema().validate(
            {"username": "user-name!", "email": "u@mail.com", "password": "Valid1234"}
        )["username"]
