import grpc
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request
from google.protobuf.json_format import MessageToDict
import datetime


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"message": "Authentication required", "error": str(e)}), 401

    return decorated


def get_post_service_stub():
    from config import Config
    import post_service_pb2_grpc

    channel = grpc.insecure_channel(Config.POST_SERVICE_GRPC)

    return post_service_pb2_grpc.PostServiceStub(channel)


def proto_timestamp_to_datetime(timestamp):
    dt = datetime.datetime.fromtimestamp(
        timestamp.seconds + timestamp.nanos / 1e9, tz=datetime.timezone.utc
    )
    return dt.isoformat()


def proto_post_to_dict(post):
    post_dict = MessageToDict(post, preserving_proto_field_name=True)

    if "created_at" in post_dict:
        post_dict["created_at"] = proto_timestamp_to_datetime(post.created_at)
    if "updated_at" in post_dict:
        post_dict["updated_at"] = proto_timestamp_to_datetime(post.updated_at)

    return post_dict
