import pytest
from utils.auth import token_required
from flask import jsonify


def test_token_required_valid_token(app, token_header):
    @app.route("/test-auth")
    @token_required
    def test_endpoint():
        return jsonify({"success": True}), 200

    with app.test_client() as client:
        response = client.get("/test-auth", headers=token_header)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


def test_token_required_missing_token(app):
    @app.route("/test-auth")
    @token_required
    def test_endpoint():
        return jsonify({"success": True}), 200

    with app.test_client() as client:
        response = client.get("/test-auth")
        assert response.status_code == 401
        data = response.get_json()
        assert "Authentication required" in data["message"]


def test_token_required_invalid_token(app):
    @app.route("/test-auth")
    @token_required
    def test_endpoint():
        return jsonify({"success": True}), 200

    with app.test_client() as client:
        response = client.get(
            "/test-auth", headers={"Authorization": "Bearer invalid.token.format"}
        )
        assert response.status_code == 401
        data = response.get_json()
        assert "Authentication required" in data["message"]


def test_token_required_expired_token(app):
    import jwt
    import datetime

    expired_token = jwt.encode(
        {"sub": 1, "exp": datetime.datetime.utcnow() - datetime.timedelta(hours=1)},
        "test-jwt-secret-key",
        algorithm="HS256",
    )

    @app.route("/test-auth")
    @token_required
    def test_endpoint():
        return jsonify({"success": True}), 200

    with app.test_client() as client:
        response = client.get(
            "/test-auth", headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        data = response.get_json()
        assert "Authentication required" in data["message"]


def test_token_required_get_identity(app, token_header):
    from flask_jwt_extended import get_jwt_identity

    @app.route("/test-identity")
    @token_required
    def test_endpoint():
        user_id = get_jwt_identity()
        return jsonify({"user_id": user_id}), 200

    with app.test_client() as client:
        response = client.get("/test-identity", headers=token_header)
        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == 1
