from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity

from services.user_service import UserService
from utils.validators import RegisterSchema, LoginSchema, ProfileUpdateSchema
from utils.auth import token_required

user_bp = Blueprint("user", __name__)


@user_bp.route("/api/users/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        errors = RegisterSchema().validate(data)
        if errors:
            return jsonify({"message": "Validation error", "errors": errors}), 400

        user = UserService.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            phone_number=data.get("phone_number"),
        )

        if isinstance(user, dict) and "error" in user:
            return jsonify({"message": user["error"]}), 400

        access_token = create_access_token(identity=user.id)

        return (
            jsonify(
                {
                    "message": "User registered successfully",
                    "user_id": user.id,
                    "username": user.username,
                    "access_token": access_token,
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"message": "Registration failed", "error": str(e)}), 500


@user_bp.route("/api/users/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        errors = LoginSchema().validate(data)
        if errors:
            return jsonify({"message": "Validation error", "errors": errors}), 400

        user = UserService.get_user_by_username(data["username"])
        if not user or not user.check_password(data["password"]):
            return jsonify({"message": "Invalid username or password"}), 401

        access_token = create_access_token(identity=user.id)

        return (
            jsonify(
                {
                    "message": "Login successful",
                    "user_id": user.id,
                    "username": user.username,
                    "access_token": access_token,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Login failed", "error": str(e)}), 500


@user_bp.route("/api/users/profile", methods=["GET"])
@token_required
def get_profile():
    try:
        user_id = get_jwt_identity()
        user = UserService.get_user_by_id(user_id)

        if not user:
            return jsonify({"message": "User not found"}), 404

        profile_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone_number": user.phone_number,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }

        if user.profile:
            profile_data.update(
                {
                    "first_name": user.profile.first_name,
                    "last_name": user.profile.last_name,
                    "birthdate": (
                        user.profile.birthdate.isoformat()
                        if user.profile.birthdate
                        else None
                    ),
                    "bio": user.profile.bio,
                    "location": user.profile.location,
                }
            )

        return jsonify(profile_data), 200

    except Exception as e:
        return jsonify({"message": "Failed to get profile", "error": str(e)}), 500


@user_bp.route("/api/users/profile", methods=["PUT"])
@token_required
def update_profile():
    try:
        user_id = get_jwt_identity()

        data = request.get_json()
        errors = ProfileUpdateSchema().validate(data)
        if errors:
            return jsonify({"message": "Validation error", "errors": errors}), 400

        result = UserService.update_profile(user_id, data)

        if isinstance(result, dict) and "error" in result:
            return jsonify({"message": result["error"]}), 400

        if not result:
            return jsonify({"message": "User not found"}), 404

        return jsonify({"message": "Profile updated successfully"}), 200

    except Exception as e:
        return jsonify({"message": "Failed to update profile", "error": str(e)}), 500
