import re
from marshmallow import Schema, fields, validates, ValidationError
from datetime import datetime

class RegisterSchema(Schema):
    username = fields.String(required=True)
    email = fields.Email(required=True)
    password = fields.String(required=True)
    phone_number = fields.String(required=False, allow_none=True)

    @validates('username')
    def validate_username(self, value):
        if len(value) < 4:
            raise ValidationError('Username must be at least 4 characters long')
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise ValidationError('Username can only contain letters, numbers, and underscores')

    @validates('password')
    def validate_password(self, value):
        if len(value) < 8:
            raise ValidationError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', value):
            raise ValidationError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', value):
            raise ValidationError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', value):
            raise ValidationError('Password must contain at least one number')

    @validates('phone_number')
    def validate_phone(self, value):
        if value and not re.match(r'^\+?[0-9]{10,15}$', value):
            raise ValidationError('Invalid phone number format')

class LoginSchema(Schema):
    username = fields.String(required=True)
    password = fields.String(required=True)

class ProfileUpdateSchema(Schema):
    first_name = fields.String(allow_none=True)
    last_name = fields.String(allow_none=True)
    birthdate = fields.Date(allow_none=True)
    bio = fields.String(allow_none=True)
    location = fields.String(allow_none=True)
    email = fields.Email(allow_none=True)
    phone_number = fields.String(allow_none=True)

    @validates('birthdate')
    def validate_birthdate(self, value):
        if value and value > datetime.now().date():
            raise ValidationError('Birthdate cannot be in the future')

    @validates('phone_number')
    def validate_phone(self, value):
        if value and not re.match(r'^\+?[0-9]{10,15}$', value):
            raise ValidationError('Invalid phone number format')