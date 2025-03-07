import json


def test_register_proxy(client, mock_requests):
    mock_requests.post.return_value.json.return_value = {
        "message": "User registered successfully",
        "user_id": 1,
        "username": "testuser",
        "access_token": "mock_token",
    }
    mock_requests.post.return_value.status_code = 201

    response = client.post(
        "/api/users/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "QWERTY123",
        },
    )

    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["message"] == "User registered successfully"
    assert data["user_id"] == 1
    assert data["username"] == "testuser"
    assert "access_token" in data
    mock_requests.post.assert_called_once()


def test_login_proxy(client, mock_requests):
    mock_requests.post.return_value.json.return_value = {
        "message": "Login successful",
        "user_id": 1,
        "username": "testuser",
        "access_token": "mock_token",
    }
    mock_requests.post.return_value.status_code = 200

    response = client.post(
        "/api/users/login", json={"username": "testuser", "password": "Password123"}
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Login successful"
    assert "access_token" in data
    mock_requests.post.assert_called_once()


def test_get_profile_proxy(client, mock_requests):
    mock_requests.get.return_value.json.return_value = {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
    }
    mock_requests.get.return_value.status_code = 200

    response = client.get(
        "/api/users/profile", headers={"Authorization": "Bearer mock_token"}
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    mock_requests.get.assert_called_once()


def test_update_profile_proxy(client, mock_requests):
    mock_requests.put.return_value.json.return_value = {
        "message": "Profile updated successfully"
    }
    mock_requests.put.return_value.status_code = 200

    response = client.put(
        "/api/users/profile",
        json={"first_name": "John", "last_name": "Doe"},
        headers={"Authorization": "Bearer mock_token"},
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Profile updated successfully"
    mock_requests.put.assert_called_once()


def test_forward_headers(client, mock_requests):
    mock_requests.get.return_value.json.return_value = {"message": "Success"}
    mock_requests.get.return_value.status_code = 200

    client.get(
        "/api/users/profile",
        headers={"Authorization": "Bearer mock_token", "Custom-Header": "Custom-Value"},
    )

    called_kwargs = mock_requests.get.call_args[1]
    headers = called_kwargs.get("headers", {})
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer mock_token"
    assert "Custom-Header" in headers
    assert headers["Custom-Header"] == "Custom-Value"
