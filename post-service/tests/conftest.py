import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from google.protobuf.timestamp_pb2 import Timestamp

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import post_service_pb2

from tests.mocks.db import (
    MockSession,
    MockPost,
    MockTag,
    mock_post1,
    mock_post2,
    mock_post3,
    mock_posts,
    setup_mock_queries,
)


@pytest.fixture
def mock_session():
    session = MockSession()
    return setup_mock_queries(session)


@pytest.fixture
def mock_db():
    mock_db = MagicMock()
    mock_db.Session.return_value = MockSession()
    return mock_db


@pytest.fixture
def post_servicer():
    from server import PostServiceServicer

    with patch("server.Post", MockPost), patch("server.Tag", MockTag), patch(
        "server.Session", return_value=MockSession()
    ):

        servicer = PostServiceServicer()
        yield servicer


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.set_code = MagicMock()
    context.set_details = MagicMock()
    return context


@pytest.fixture
def timestamp_now():
    timestamp = Timestamp()
    timestamp.GetCurrentTime()
    return timestamp


@pytest.fixture
def create_post_request():
    return post_service_pb2.CreatePostRequest(
        title="Test Post",
        description="This is a test post",
        creator_id=1,
        is_private=False,
        tags=["tech", "testing"],
    )


@pytest.fixture
def get_post_request():
    return post_service_pb2.GetPostRequest(post_id=1, requester_id=1)


@pytest.fixture
def list_posts_request():
    return post_service_pb2.ListPostsRequest(
        page=1, per_page=10, requester_id=1, only_own=False, tags=[]
    )


@pytest.fixture
def update_post_request():
    return post_service_pb2.UpdatePostRequest(
        post_id=1,
        updater_id=1,
        title="Updated Post",
        description="This post has been updated",
        is_private=True,
        tags=["tech", "updated"],
    )


@pytest.fixture
def delete_post_request():
    return post_service_pb2.DeletePostRequest(post_id=1, requester_id=1)
