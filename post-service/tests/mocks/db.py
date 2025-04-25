from unittest.mock import MagicMock
import datetime


class MockBase:
    metadata = MagicMock()


class MockTable:
    def __init__(self, name, metadata, *args, **kwargs):
        self.name = name
        self.metadata = metadata


class MockColumn:
    def __init__(
        self,
        type_,
        primary_key=False,
        nullable=True,
        unique=False,
        default=None,
        onupdate=None,
        **kwargs
    ):
        self.type_ = type_
        self.primary_key = primary_key
        self.nullable = nullable
        self.unique = unique
        self.default = default
        self.onupdate = onupdate


class MockTag:
    def __init__(self, id=None, name=None):
        self.id = id
        self.name = name


class MockPost:
    def __init__(
        self,
        id=None,
        title=None,
        description=None,
        creator_id=None,
        is_private=False,
        created_at=None,
        updated_at=None,
        tags=None,
    ):
        self.id = id
        self.title = title
        self.description = description
        self.creator_id = creator_id
        self.is_private = is_private
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()
        self.tags = tags or []


class MockQuery:
    def __init__(self, return_value=None):
        self.return_value = return_value
        self.filters = []
        self.order_by_clauses = []
        self.offset_value = None
        self.limit_value = None

    def filter_by(self, **kwargs):
        self.filters.append(kwargs)
        return self

    def filter(self, *args):
        self.filters.append(args)
        return self

    def join(self, *args):
        return self

    def order_by(self, *order_by_clauses):
        self.order_by_clauses.extend(order_by_clauses)
        return self

    def offset(self, offset_value):
        self.offset_value = offset_value
        return self

    def limit(self, limit_value):
        self.limit_value = limit_value
        return self

    def first(self):
        if isinstance(self.return_value, list) and self.return_value:
            return self.return_value[0]
        return self.return_value

    def all(self):
        if isinstance(self.return_value, list):
            return self.return_value
        elif self.return_value is None:
            return []
        else:
            return [self.return_value]

    def count(self):
        if isinstance(self.return_value, list):
            return len(self.return_value)
        elif self.return_value is None:
            return 0
        else:
            return 1

    def get(self, id):
        if isinstance(self.return_value, list):
            for item in self.return_value:
                if getattr(item, "id", None) == id:
                    return item
        elif getattr(self.return_value, "id", None) == id:
            return self.return_value
        return None


class MockSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.added_objects = []
        self.deleted_objects = []
        self.queries = {}

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def add(self, obj):
        self.added_objects.append(obj)

    def delete(self, obj):
        self.deleted_objects.append(obj)

    def query(self, model):
        if model not in self.queries:
            self.queries[model] = MockQuery()
        return self.queries[model]

    def execute(self, query):
        return MagicMock()

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()


# Мок для SQLAlchemy Engine
class MockEngine:
    def __init__(self):
        self.url = "sqlite:///:memory:"

    def connect(self):
        return MagicMock()

    def dispose(self):
        pass


mock_engine = MockEngine()
mock_session_factory = MagicMock(return_value=MockSession())
mock_post_tags = MockTable("post_tags", None)

MockTag = MagicMock()
MockTag.query = MockQuery()
MockTag.return_value = MockTag()
MockTag.return_value.id = 1
MockTag.return_value.name = "test_tag"

MockPost = MagicMock()
MockPost.query = MockQuery()
MockPost.return_value = MockPost()
MockPost.return_value.id = 1
MockPost.return_value.title = "Test Post"
MockPost.return_value.description = "Test Description"
MockPost.return_value.creator_id = 1
MockPost.return_value.is_private = False
MockPost.return_value.created_at = datetime.datetime.utcnow()
MockPost.return_value.updated_at = datetime.datetime.utcnow()
MockPost.return_value.tags = []

mock_post1 = MockPost(
    id=1,
    title="First Post",
    description="Description of first post",
    creator_id=1,
    is_private=False,
    tags=[MockTag(id=1, name="tech"), MockTag(id=2, name="python")],
)

mock_post2 = MockPost(
    id=2,
    title="Second Post",
    description="Description of second post",
    creator_id=1,
    is_private=True,
    tags=[MockTag(id=1, name="tech")],
)

mock_post3 = MockPost(
    id=3,
    title="Third Post",
    description="Description of third post",
    creator_id=2,
    is_private=False,
    tags=[MockTag(id=3, name="news")],
)

mock_posts = [mock_post1, mock_post2, mock_post3]


def setup_mock_queries(session):
    mock_post_query = MockQuery(mock_posts)
    mock_tag_query = MockQuery([tag for post in mock_posts for tag in post.tags])

    session.queries[MockPost] = mock_post_query
    session.queries[MockTag] = mock_tag_query

    return session
