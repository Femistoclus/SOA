from flask import Flask, request, jsonify
import requests
import grpc
from flask_jwt_extended import JWTManager, get_jwt_identity

from config import Config
from utils.validators import CreatePostSchema, UpdatePostSchema, ListPostsSchema
from utils.utils import (
    proto_timestamp_to_datetime,
    token_required,
    get_post_service_stub,
    proto_post_to_dict,
)

import post_service_pb2


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    jwt = JWTManager(app)

    @app.route("/api/users/register", methods=["POST"])
    def register():
        return proxy_request("POST", "/api/users/register")

    @app.route("/api/users/login", methods=["POST"])
    def login():
        return proxy_request("POST", "/api/users/login")

    @app.route("/api/users/profile", methods=["GET"])
    def get_profile():
        return proxy_request("GET", "/api/users/profile")

    @app.route("/api/users/profile", methods=["PUT"])
    def update_profile():
        return proxy_request("PUT", "/api/users/profile")

    def proxy_request(method, path):
        url = f"{app.config['USER_SERVICE_URL']}{path}"

        headers = {key: value for key, value in request.headers if key != "Host"}

        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=request.get_json(), headers=headers)
        elif method == "PUT":
            response = requests.put(url, json=request.get_json(), headers=headers)

        return jsonify(response.json()), response.status_code

    @app.route("/api/posts", methods=["POST"])
    @token_required
    def create_post():
        try:
            user_id = get_jwt_identity()

            data = request.get_json()
            errors = CreatePostSchema().validate(data)
            if errors:
                return jsonify({"message": "Validation error", "errors": errors}), 400

            stub = get_post_service_stub()

            grpc_request = post_service_pb2.CreatePostRequest(
                title=data["title"],
                description=data["description"],
                creator_id=user_id,
                is_private=data.get("is_private", False),
                tags=data.get("tags", []),
            )

            response = stub.CreatePost(grpc_request)
            post_data = proto_post_to_dict(response)

            return jsonify(post_data), 201
        except grpc.RpcError as e:
            status_code = e.code().value[0]
            return (
                jsonify({"message": f"Error creating post: {e.details()}"}),
                status_code,
            )
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    @app.route("/api/posts/<int:post_id>", methods=["GET"])
    @token_required
    def get_post(post_id):
        try:
            user_id = get_jwt_identity()
            stub = get_post_service_stub()

            grpc_request = post_service_pb2.GetPostRequest(
                post_id=post_id, requester_id=user_id
            )

            response = stub.GetPost(grpc_request)

            post_data = proto_post_to_dict(response)

            return jsonify(post_data), 200
        except grpc.RpcError as e:
            status_code = e.code().value[0]
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return jsonify({"message": "Post not found"}), 404
            elif e.code() == grpc.StatusCode.PERMISSION_DENIED:
                return jsonify({"message": "Access denied to private post"}), 403
            return (
                jsonify({"message": f"Error getting post: {e.details()}"}),
                status_code,
            )
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    @app.route("/api/posts", methods=["GET"])
    @token_required
    def list_posts():
        try:
            user_id = get_jwt_identity()

            args = {}
            for param in ["page", "per_page", "only_own"]:
                if param in request.args:
                    if param in ["page", "per_page"]:
                        args[param] = int(request.args.get(param, 1))
                    elif param == "only_own":
                        args[param] = request.args.get(param, "").lower() == "true"

            if "tags" in request.args:
                args["tags"] = request.args.getlist("tags")

            errors = ListPostsSchema().validate(args)
            if errors:
                return jsonify({"message": "Validation error", "errors": errors}), 400

            stub = get_post_service_stub()

            grpc_request = post_service_pb2.ListPostsRequest(
                page=args.get("page", 1),
                per_page=args.get("per_page", 10),
                requester_id=user_id,
                only_own=args.get("only_own", False),
                tags=args.get("tags", []),
            )

            response = stub.ListPosts(grpc_request)

            result = {
                "posts": [proto_post_to_dict(post) for post in response.posts],
                "total_count": response.total_count,
                "total_pages": response.total_pages,
                "page": args.get("page", 1),
                "per_page": args.get("per_page", 10),
            }

            return jsonify(result), 200
        except grpc.RpcError as e:
            status_code = e.code().value[0]
            return (
                jsonify({"message": f"Error listing posts: {e.details()}"}),
                status_code,
            )
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    @app.route("/api/posts/<int:post_id>", methods=["PUT"])
    @token_required
    def update_post(post_id):
        try:
            user_id = get_jwt_identity()

            data = request.get_json()
            errors = UpdatePostSchema().validate(data)
            if errors:
                return jsonify({"message": "Validation error", "errors": errors}), 400

            stub = get_post_service_stub()

            grpc_request = post_service_pb2.UpdatePostRequest(
                post_id=post_id, updater_id=user_id
            )

            if "title" in data:
                grpc_request.title = data["title"]
            if "description" in data:
                grpc_request.description = data["description"]
            if "is_private" in data:
                grpc_request.is_private = data["is_private"]
            if "tags" in data:
                grpc_request.tags.extend(data["tags"])

            response = stub.UpdatePost(grpc_request)

            post_data = proto_post_to_dict(response)

            return jsonify(post_data), 200
        except grpc.RpcError as e:
            status_code = e.code().value[0]
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return jsonify({"message": "Post not found"}), 404
            elif e.code() == grpc.StatusCode.PERMISSION_DENIED:
                return (
                    jsonify({"message": "Only the creator can update this post"}),
                    403,
                )
            return (
                jsonify({"message": f"Error updating post: {e.details()}"}),
                status_code,
            )
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    @app.route("/api/posts/<int:post_id>", methods=["DELETE"])
    @token_required
    def delete_post(post_id):
        try:
            user_id = get_jwt_identity()

            stub = get_post_service_stub()

            grpc_request = post_service_pb2.DeletePostRequest(
                post_id=post_id, requester_id=user_id
            )

            stub.DeletePost(grpc_request)

            return jsonify({"message": "Post deleted successfully"}), 200
        except grpc.RpcError as e:
            status_code = e.code().value[0]
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return jsonify({"message": "Post not found"}), 404
            elif e.code() == grpc.StatusCode.PERMISSION_DENIED:
                return (
                    jsonify({"message": "Only the creator can delete this post"}),
                    403,
                )
            return (
                jsonify({"message": f"Error deleting post: {e.details()}"}),
                status_code,
            )
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    @app.route("/api/posts/<int:post_id>/view", methods=["POST"])
    @token_required
    def view_post(post_id):
        try:
            user_id = get_jwt_identity()
            stub = get_post_service_stub()

            grpc_request = post_service_pb2.ViewPostRequest(
                post_id=post_id, viewer_id=user_id
            )

            response = stub.ViewPost(grpc_request)

            return (
                jsonify(
                    {"success": response.success, "views_count": response.views_count}
                ),
                200,
            )
        except grpc.RpcError as e:
            status_code = e.code().value[0]
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return jsonify({"message": "Post not found"}), 404
            return (
                jsonify({"message": f"Error viewing post: {e.details()}"}),
                status_code,
            )
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    @app.route("/api/posts/<int:post_id>/like", methods=["POST"])
    @token_required
    def like_post(post_id):
        try:
            user_id = get_jwt_identity()
            stub = get_post_service_stub()

            grpc_request = post_service_pb2.LikePostRequest(
                post_id=post_id, user_id=user_id
            )

            response = stub.LikePost(grpc_request)

            return (
                jsonify(
                    {"success": response.success, "likes_count": response.likes_count}
                ),
                200,
            )
        except grpc.RpcError as e:
            status_code = e.code().value[0]
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return jsonify({"message": "Post not found"}), 404
            return (
                jsonify({"message": f"Error liking post: {e.details()}"}),
                status_code,
            )
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    @app.route("/api/posts/<int:post_id>/comments", methods=["POST"])
    @token_required
    def add_comment(post_id):
        try:
            user_id = get_jwt_identity()

            data = request.get_json()
            if not data or not "text" in data or not data["text"].strip():
                return jsonify({"message": "Comment text is required"}), 400

            stub = get_post_service_stub()

            grpc_request = post_service_pb2.AddCommentRequest(
                post_id=post_id, user_id=user_id, text=data["text"]
            )

            response = stub.AddComment(grpc_request)

            created_at = proto_timestamp_to_datetime(response.created_at)

            return (
                jsonify(
                    {
                        "id": response.id,
                        "post_id": response.post_id,
                        "user_id": response.user_id,
                        "text": response.text,
                        "created_at": created_at,
                    }
                ),
                201,
            )
        except grpc.RpcError as e:
            status_code = e.code().value[0]
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return jsonify({"message": "Post not found"}), 404
            return (
                jsonify({"message": f"Error adding comment: {e.details()}"}),
                status_code,
            )
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    @app.route("/api/posts/<int:post_id>/comments", methods=["GET"])
    @token_required
    def get_comments(post_id):
        try:
            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("per_page", 10, type=int)

            if page < 1:
                return jsonify({"message": "Page must be a positive integer"}), 400
            if per_page < 1 or per_page > 100:
                return jsonify({"message": "per_page must be between 1 and 100"}), 400

            stub = get_post_service_stub()

            grpc_request = post_service_pb2.GetCommentsRequest(
                post_id=post_id, page=page, per_page=per_page
            )

            response = stub.GetComments(grpc_request)

            comments = []
            for comment in response.comments:
                comments.append(
                    {
                        "id": comment.id,
                        "post_id": comment.post_id,
                        "user_id": comment.user_id,
                        "text": comment.text,
                        "created_at": proto_timestamp_to_datetime(comment.created_at),
                    }
                )

            return (
                jsonify(
                    {
                        "comments": comments,
                        "total_count": response.total_count,
                        "total_pages": response.total_pages,
                        "page": page,
                        "per_page": per_page,
                    }
                ),
                200,
            )
        except grpc.RpcError as e:
            status_code = e.code().value[0]
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return jsonify({"message": "Post not found"}), 404
            return (
                jsonify({"message": f"Error getting comments: {e.details()}"}),
                status_code,
            )
        except Exception as e:
            return jsonify({"message": f"Error: {str(e)}"}), 500

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "healthy", "message": "API Gateway is up"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
