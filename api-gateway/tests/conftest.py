import pytest
from unittest.mock import patch, MagicMock
from app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        'TESTING': True,
        'USER_SERVICE_URL': 'http://mock-user-service:5001'
    })
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def mock_requests():
    with patch('app.requests') as mock_requests:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Mock response"}
        mock_requests.get.return_value = mock_response
        mock_requests.post.return_value = mock_response
        mock_requests.put.return_value = mock_response
        yield mock_requests
