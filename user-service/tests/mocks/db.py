from unittest.mock import MagicMock
import datetime


class MockQuery:
    def __init__(self, return_value=None):
        self.return_value = return_value
        self.filters = []

    def filter_by(self, **kwargs):
        self.filters.append(kwargs)
        return self

    def filter(self, *args):
        self.filters.append(args)
        return self

    def first(self):
        return self.return_value

    def all(self):
        if isinstance(self.return_value, list):
            return self.return_value
        elif self.return_value is None:
            return []
        else:
            return [self.return_value]

    def get(self, id):
        if self.return_value and getattr(self.return_value, "id", None) == id:
            return self.return_value
        return None


class MockModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        if not hasattr(self, "id"):
            self.id = 1
        if not hasattr(self, "created_at"):
            self.created_at = datetime.datetime.now()
        if not hasattr(self, "updated_at"):
            self.updated_at = datetime.datetime.now()


class MockSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.added_objects = []
        self.deleted_objects = []

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def add(self, obj):
        self.added_objects.append(obj)

    def delete(self, obj):
        self.deleted_objects.append(obj)


class MockDB:
    def __init__(self):
        self.session = MockSession()

    def create_all(self):
        pass

    def drop_all(self):
        pass


mock_user = MockModel(
    id=1,
    username="testuser",
    email="test@example.com",
    password_hash="hashed_password",
    phone_number="+12345678901",
    check_password=MagicMock(return_value=True),
    set_password=MagicMock(),
    profile=MockModel(
        id=1,
        first_name="John",
        last_name="Doe",
        birthdate=datetime.date(1990, 1, 1),
        bio="Test bio",
        location="Test location",
    ),
    roles=[MockModel(id=1, role="user", description="Regular user")],
)

mock_db = MockDB()
mock_user_query = MockQuery(mock_user)

MockUser = MagicMock()
MockUser.query = mock_user_query

MockUserProfile = MagicMock()
MockUserProfile.query = MockQuery()

MockUserRole = MagicMock()
MockUserRole.query = MockQuery()
