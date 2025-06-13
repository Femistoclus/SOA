from datetime import datetime
import grpc
import logging
import sys
import json

from concurrent import futures
from sqlalchemy.exc import SQLAlchemyError
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.empty_pb2 import Empty

import post_service_pb2
import post_service_pb2_grpc

from models.post import Post, Tag, Session, create_tables, PostView, PostLike, Comment

from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers="kafka:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

MAX_WORKERS = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


class PostServiceServicer(post_service_pb2_grpc.PostServiceServicer):
    """Реализация gRPC сервиса для работы с постами"""

    def CreatePost(self, request, context):
        """Создание нового поста"""
        session = Session()
        try:
            post = Post(
                title=request.title,
                description=request.description,
                creator_id=request.creator_id,
                is_private=request.is_private,
            )

            for tag_name in request.tags:
                tag = session.query(Tag).filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                post.tags.append(tag)

            session.add(post)
            session.commit()

            response = post_service_pb2.Post(
                id=post.id,
                title=post.title,
                description=post.description,
                creator_id=post.creator_id,
                is_private=post.is_private,
                tags=[tag.name for tag in post.tags],
            )

            created_at = Timestamp()
            created_at.FromDatetime(post.created_at)
            response.created_at.CopyFrom(created_at)

            updated_at = Timestamp()
            updated_at.FromDatetime(post.updated_at)
            response.updated_at.CopyFrom(updated_at)

            return response
        except SQLAlchemyError as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return post_service_pb2.Post()
        finally:
            session.close()

    def GetPost(self, request, context):
        """Получение поста по ID"""
        session = Session()
        try:
            post = session.query(Post).get(request.post_id)

            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.Post()

            if post.is_private and post.creator_id != request.requester_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("Access denied to private post")
                return post_service_pb2.Post()

            response = post_service_pb2.Post(
                id=post.id,
                title=post.title,
                description=post.description,
                creator_id=post.creator_id,
                is_private=post.is_private,
                tags=[tag.name for tag in post.tags],
            )

            created_at = Timestamp()
            created_at.FromDatetime(post.created_at)
            response.created_at.CopyFrom(created_at)

            updated_at = Timestamp()
            updated_at.FromDatetime(post.updated_at)
            response.updated_at.CopyFrom(updated_at)

            return response
        except SQLAlchemyError as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return post_service_pb2.Post()
        finally:
            session.close()

    def ListPosts(self, request, context):
        """Получение списка постов с пагинацией"""
        session = Session()
        try:
            page = max(1, request.page)
            per_page = min(max(1, request.per_page), 100)

            query = session.query(Post)

            if request.tags:
                query = query.join(Post.tags).filter(Tag.name.in_(request.tags))

            if request.only_own:
                query = query.filter(Post.creator_id == request.requester_id)
            else:
                query = query.filter(
                    (Post.is_private == False)
                    | (
                        (Post.is_private == True)
                        & (Post.creator_id == request.requester_id)
                    )
                )

            total_count = query.count()
            total_pages = (total_count + per_page - 1) // per_page

            posts = (
                query.order_by(Post.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )

            response = post_service_pb2.ListPostsResponse(
                total_count=total_count, total_pages=total_pages
            )

            for post in posts:
                post_proto = post_service_pb2.Post(
                    id=post.id,
                    title=post.title,
                    description=post.description,
                    creator_id=post.creator_id,
                    is_private=post.is_private,
                    tags=[tag.name for tag in post.tags],
                )

                created_at = Timestamp()
                created_at.FromDatetime(post.created_at)
                post_proto.created_at.CopyFrom(created_at)

                updated_at = Timestamp()
                updated_at.FromDatetime(post.updated_at)
                post_proto.updated_at.CopyFrom(updated_at)

                response.posts.append(post_proto)

            return response
        except SQLAlchemyError as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return post_service_pb2.ListPostsResponse()
        finally:
            session.close()

    def UpdatePost(self, request, context):
        """Обновление существующего поста"""
        session = Session()
        try:
            post = session.query(Post).get(request.post_id)

            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.Post()

            if post.creator_id != request.updater_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("Only the creator can update this post")
                return post_service_pb2.Post()

            if request.title:
                post.title = request.title
            if request.description:
                post.description = request.description

            post.is_private = request.is_private

            if request.tags:
                post.tags.clear()

                for tag_name in request.tags:
                    tag = session.query(Tag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        session.add(tag)
                    post.tags.append(tag)

            session.commit()

            response = post_service_pb2.Post(
                id=post.id,
                title=post.title,
                description=post.description,
                creator_id=post.creator_id,
                is_private=post.is_private,
                tags=[tag.name for tag in post.tags],
            )

            created_at = Timestamp()
            created_at.FromDatetime(post.created_at)
            response.created_at.CopyFrom(created_at)

            updated_at = Timestamp()
            updated_at.FromDatetime(post.updated_at)
            response.updated_at.CopyFrom(updated_at)

            return response
        except SQLAlchemyError as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return post_service_pb2.Post()
        finally:
            session.close()

    def DeletePost(self, request, context):
        """Удаление поста"""
        session = Session()
        try:
            post = session.query(Post).get(request.post_id)

            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return Empty()

            if post.creator_id != request.requester_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("Only the creator can delete this post")
                return Empty()

            session.delete(post)
            session.commit()

            return Empty()
        except SQLAlchemyError as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return Empty()
        finally:
            session.close()

    def ViewPost(self, request, context):
        """Записывает просмотр поста и отправляет событие в Kafka"""
        session = Session()
        try:
            post = session.query(Post).get(request.post_id)
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.ViewPostResponse()

            if post.is_private and post.creator_id != request.viewer_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details(
                    "Cannot view a private post you don't have access to"
                )
                return post_service_pb2.Comment()

            # Если юзер уже посмотрел - я решил не отправлять еще раз
            existing_view = (
                session.query(PostView)
                .filter_by(post_id=request.post_id, user_id=request.viewer_id)
                .first()
            )

            if not existing_view:
                view = PostView(post_id=request.post_id, user_id=request.viewer_id)
                session.add(view)
                session.commit()

                event = {
                    "event_type": "post_viewed",
                    "post_id": request.post_id,
                    "user_id": request.viewer_id,
                    "timestamp": datetime.now().isoformat(),
                }
                producer.send("post-views", event)

            views_count = (
                session.query(PostView).filter_by(post_id=request.post_id).count()
            )

            return post_service_pb2.ViewPostResponse(
                success=True, views_count=views_count
            )

        except SQLAlchemyError as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return post_service_pb2.ViewPostResponse()
        finally:
            session.close()

    def LikePost(self, request, context):
        """Обрабатывает лайки постов и отправляет событие в Kafka"""
        session = Session()
        try:
            post = session.query(Post).get(request.post_id)
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.LikePostResponse()

            if post.is_private and post.creator_id != request.user_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details(
                    "Cannot like a private post you don't have access to"
                )
                return post_service_pb2.Comment()

            existing_like = (
                session.query(PostLike)
                .filter_by(post_id=request.post_id, user_id=request.user_id)
                .first()
            )

            if existing_like:
                # Если уже поставил лайк - удаляем, как например в tg
                session.delete(existing_like)
                session.commit()
            else:
                like = PostLike(post_id=request.post_id, user_id=request.user_id)
                session.add(like)
                session.commit()

                event = {
                    "event_type": "post_liked",
                    "post_id": request.post_id,
                    "user_id": request.user_id,
                    "timestamp": datetime.now().isoformat(),
                }
                producer.send("post-interactions", event)

            likes_count = (
                session.query(PostLike).filter_by(post_id=request.post_id).count()
            )

            return post_service_pb2.LikePostResponse(
                success=True, likes_count=likes_count
            )

        except SQLAlchemyError as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return post_service_pb2.LikePostResponse()
        finally:
            session.close()

    def AddComment(self, request, context):
        """Добавляет комментарий к посту и отправляет событие в Kafka"""
        session = Session()
        try:
            post = session.query(Post).get(request.post_id)
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.Comment()

            if post.is_private and post.creator_id != request.user_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details(
                    "Cannot comment on a private post you don't have access to"
                )
                return post_service_pb2.Comment()

            comment = Comment(
                post_id=request.post_id, user_id=request.user_id, text=request.text
            )
            session.add(comment)
            session.commit()

            event = {
                "event_type": "post_commented",
                "post_id": request.post_id,
                "user_id": request.user_id,
                "comment_id": comment.id,
                "timestamp": datetime.now().isoformat(),
            }
            producer.send("post-comments", event)

            response = post_service_pb2.Comment(
                id=comment.id,
                post_id=comment.post_id,
                user_id=comment.user_id,
                text=comment.text,
            )

            created_at = Timestamp()
            created_at.FromDatetime(comment.created_at)
            response.created_at.CopyFrom(created_at)

            return response

        except SQLAlchemyError as e:
            session.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return post_service_pb2.Comment()
        finally:
            session.close()

    def GetComments(self, request, context):
        """Получает список комментариев к посту с пагинацией"""
        session = Session()
        try:
            post = session.query(Post).get(request.post_id)
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return post_service_pb2.GetCommentsResponse()
            
            if post.is_private and post.creator_id != request.requester_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("Cannot view comments on a private post you don't have access to")
                return post_service_pb2.GetCommentsResponse()

            page = max(1, request.page)
            per_page = min(max(1, request.per_page), 100)

            query = session.query(Comment).filter_by(post_id=request.post_id)
            total_count = query.count()
            total_pages = (total_count + per_page - 1) // per_page

            comments = (
                query.order_by(Comment.created_at.asc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )

            response = post_service_pb2.GetCommentsResponse(
                total_count=total_count, total_pages=total_pages
            )

            for comment in comments:
                comment_proto = post_service_pb2.Comment(
                    id=comment.id,
                    post_id=comment.post_id,
                    user_id=comment.user_id,
                    text=comment.text,
                )

                created_at = Timestamp()
                created_at.FromDatetime(comment.created_at)
                comment_proto.created_at.CopyFrom(created_at)

                response.comments.append(comment_proto)

            return response

        except SQLAlchemyError as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {str(e)}")
            return post_service_pb2.GetCommentsResponse()
        finally:
            session.close()


def serve():
    create_tables()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
    post_service_pb2_grpc.add_PostServiceServicer_to_server(
        PostServiceServicer(), server
    )

    server.add_insecure_port("[::]:50051")
    server.start()
    logger.info("Post service started on port 50051")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
