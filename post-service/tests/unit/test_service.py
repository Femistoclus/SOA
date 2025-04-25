import pytest
import grpc
from unittest.mock import patch, MagicMock
import datetime

from models.post import *

def test_post_tag_relationship():
    
    post = Post(
        title="Test Post",
        description="This is a test post",
        creator_id=1,
        is_private=False
    )
    
    tag1 = Tag(name="tech")
    tag2 = Tag(name="python")
    
    post.tags.append(tag1)
    post.tags.append(tag2)
    
    assert len(post.tags) == 2
    assert post.tags[0] == tag1
    assert post.tags[1] == tag2


def test_get_post_success(post_servicer, get_post_request, mock_context, mock_session):
    with patch('server.Session', return_value=mock_session):
        response = post_servicer.GetPost(get_post_request, mock_context)
        
        assert response is not None
        assert response.id == get_post_request.post_id
        assert hasattr(response, 'title')
        assert hasattr(response, 'description')
        assert hasattr(response, 'creator_id')

def test_get_post_not_found(post_servicer, mock_context):
    session = MagicMock()
    session.query().get.return_value = None
    
    with patch('server.Session', return_value=session):
        request = MagicMock()
        request.post_id = 999
        
        post_servicer.GetPost(request, mock_context)
        
        mock_context.set_code.assert_called_with(grpc.StatusCode.NOT_FOUND)

def test_get_private_post_unauthorized(post_servicer, mock_context):
    private_post = MagicMock()
    private_post.id = 2
    private_post.is_private = True
    private_post.creator_id = 1
    
    session = MagicMock()
    session.query().get.return_value = private_post
    
    with patch('server.Session', return_value=session):
        request = MagicMock()
        request.post_id = 2
        request.requester_id = 2
        
        post_servicer.GetPost(request, mock_context)
        
        mock_context.set_code.assert_called_with(grpc.StatusCode.PERMISSION_DENIED)

def test_list_posts_success(post_servicer, list_posts_request, mock_context, mock_session):
    with patch('server.Session', return_value=mock_session):
        response = post_servicer.ListPosts(list_posts_request, mock_context)
        
        assert response is not None
        assert hasattr(response, 'posts')
        assert hasattr(response, 'total_count')
        assert hasattr(response, 'total_pages')
