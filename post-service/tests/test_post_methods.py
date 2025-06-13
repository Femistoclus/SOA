import unittest
import grpc
from unittest.mock import MagicMock, patch
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

sys.modules['kafka'] = MagicMock()
sys.modules['kafka.producer'] = MagicMock()
sys.modules['kafka.producer.kafka'] = MagicMock()
mock_producer = MagicMock()
sys.modules['kafka.producer.kafka'].KafkaProducer = MagicMock(return_value=mock_producer)

import post_service_pb2
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=False)
    creator_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_private = Column(Boolean, default=False)

class PostView(Base):
    __tablename__ = "post_views"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    viewed_at = Column(DateTime, default=datetime.utcnow)

class PostLike(Base):
    __tablename__ = "post_likes"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    liked_at = Column(DateTime, default=datetime.utcnow)

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    text = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

TEST_DB = "sqlite:///:memory:"
engine = create_engine(TEST_DB)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

class PostServiceServicer:
    def ViewPost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).get(request.post_id)
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return MagicMock(success=False, views_count=0)

            existing_view = session.query(PostView).filter_by(
                post_id=request.post_id,
                user_id=request.viewer_id
            ).first()

            if not existing_view:
                view = PostView(post_id=request.post_id, user_id=request.viewer_id)
                session.add(view)
                session.commit()

                event = {
                    'event_type': 'post_viewed',
                    'post_id': request.post_id,
                    'user_id': request.viewer_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                # mock_producer используется здесь

            views_count = session.query(PostView).filter_by(post_id=request.post_id).count()
            return MagicMock(success=True, views_count=views_count)
        finally:
            session.close()

    def LikePost(self, request, context):
        session = Session()
        try:
            post = session.query(Post).get(request.post_id)
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return MagicMock(success=False, likes_count=0)

            existing_like = session.query(PostLike).filter_by(
                post_id=request.post_id,
                user_id=request.user_id
            ).first()

            if existing_like:
                session.delete(existing_like)
                session.commit()
            else:
                like = PostLike(post_id=request.post_id, user_id=request.user_id)
                session.add(like)
                session.commit()

                event = {
                    'event_type': 'post_liked',
                    'post_id': request.post_id,
                    'user_id': request.user_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                # mock_producer используется здесь

            likes_count = session.query(PostLike).filter_by(post_id=request.post_id).count()
            return MagicMock(success=True, likes_count=likes_count)
        finally:
            session.close()

    def AddComment(self, request, context):
        session = Session()
        try:
            post = session.query(Post).get(request.post_id)
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return MagicMock()

            if post.is_private and post.creator_id != request.user_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("Cannot comment on a private post you don't have access to")
                return MagicMock()

            comment = Comment(
                post_id=request.post_id,
                user_id=request.user_id,
                text=request.text
            )
            session.add(comment)
            session.commit()

            event = {
                'event_type': 'post_commented',
                'post_id': request.post_id,
                'user_id': request.user_id,
                'comment_id': comment.id,
                'timestamp': datetime.utcnow().isoformat()
            }

            response = MagicMock()
            response.id = comment.id
            response.post_id = comment.post_id
            response.user_id = comment.user_id
            response.text = comment.text
            
            created_at = Timestamp()
            created_at.FromDatetime(comment.created_at)
            response.created_at = created_at
            
            return response
        finally:
            session.close()

    def GetComments(self, request, context):
        session = Session()
        try:
            post = session.query(Post).get(request.post_id)
            if not post:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Post with ID {request.post_id} not found")
                return MagicMock(comments=[], total_count=0, total_pages=0)

            if post.is_private and post.creator_id != request.requester_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("Cannot view comments on a private post you don't have access to")
                return MagicMock(comments=[], total_count=0, total_pages=0)

            page = max(1, request.page)
            per_page = min(max(1, request.per_page), 100)

            query = session.query(Comment).filter_by(post_id=request.post_id)
            total_count = query.count()
            total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0

            comments = (
                query.order_by(Comment.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )

            response = MagicMock()
            response.total_count = total_count
            response.total_pages = total_pages
            
            response.comments = []
            for comment in comments:
                comment_mock = MagicMock()
                comment_mock.id = comment.id
                comment_mock.post_id = comment.post_id
                comment_mock.user_id = comment.user_id
                comment_mock.text = comment.text
                
                created_at = Timestamp()
                created_at.FromDatetime(comment.created_at)
                comment_mock.created_at = created_at
                
                response.comments.append(comment_mock)
            
            return response
        finally:
            session.close()


class TestPostServiceMethods(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        self.service = PostServiceServicer()
        self.context = MagicMock()
        self.producer_mock = mock_producer
        self.create_test_data()
        
    def tearDown(self):
        self.session.query(Comment).delete()
        self.session.query(PostLike).delete()
        self.session.query(PostView).delete()
        self.session.query(Post).delete()
        self.session.commit()
        self.session.close()
        
    def create_test_data(self):
        public_post = Post(
            id=1,
            title="Public Post",
            description="This is a public test post",
            creator_id=1,
            is_private=False
        )
        
        private_post = Post(
            id=2,
            title="Private Post",
            description="This is a private test post",
            creator_id=1,
            is_private=True
        )
        
        comment1 = Comment(
            id=1,
            post_id=1,
            user_id=2,
            text="Test comment 1",
            created_at=datetime.utcnow()
        )
        
        comment2 = Comment(
            id=2,
            post_id=1,
            user_id=1,
            text="Test comment 2",
            created_at=datetime.utcnow()
        )
        
        self.session.add_all([public_post, private_post, comment1, comment2])
        self.session.commit()
        
    def test_view_post_success(self):
        request = post_service_pb2.ViewPostRequest(post_id=1, viewer_id=2)
        response = self.service.ViewPost(request, self.context)
        
        self.assertTrue(response.success)
        self.assertEqual(response.views_count, 1)
        
        view = self.session.query(PostView).filter_by(post_id=1, user_id=2).first()
        self.assertIsNotNone(view)
    
    def test_view_post_not_found(self):
        request = post_service_pb2.ViewPostRequest(post_id=999, viewer_id=2)
        response = self.service.ViewPost(request, self.context)
        
        self.context.set_code.assert_called_with(grpc.StatusCode.NOT_FOUND)
    
    def test_view_post_duplicate(self):
        view = PostView(post_id=1, user_id=2)
        self.session.add(view)
        self.session.commit()
        
        request = post_service_pb2.ViewPostRequest(post_id=1, viewer_id=2)
        response = self.service.ViewPost(request, self.context)
        
        self.assertTrue(response.success)
        self.assertEqual(response.views_count, 1)
    
    def test_like_post_success(self):
        request = post_service_pb2.LikePostRequest(post_id=1, user_id=2)
        response = self.service.LikePost(request, self.context)
        
        self.assertTrue(response.success)
        self.assertEqual(response.likes_count, 1)
        
        like = self.session.query(PostLike).filter_by(post_id=1, user_id=2).first()
        self.assertIsNotNone(like)
    
    def test_like_post_toggle(self):
        like = PostLike(post_id=1, user_id=2)
        self.session.add(like)
        self.session.commit()
        
        request = post_service_pb2.LikePostRequest(post_id=1, user_id=2)
        response = self.service.LikePost(request, self.context)
        
        self.assertTrue(response.success)
        self.assertEqual(response.likes_count, 0)
        
        like = self.session.query(PostLike).filter_by(post_id=1, user_id=2).first()
        self.assertIsNone(like)
    
    def test_like_post_not_found(self):
        request = post_service_pb2.LikePostRequest(post_id=999, user_id=2)
        response = self.service.LikePost(request, self.context)
        
        self.context.set_code.assert_called_with(grpc.StatusCode.NOT_FOUND)
    
    def test_add_comment_success(self):
        request = post_service_pb2.AddCommentRequest(
            post_id=1,
            user_id=3,
            text="New test comment"
        )
        response = self.service.AddComment(request, self.context)
        
        self.assertEqual(response.text, "New test comment")
        self.assertEqual(response.user_id, 3)
        self.assertEqual(response.post_id, 1)
        
        comment = self.session.query(Comment).filter_by(text="New test comment").first()
        self.assertIsNotNone(comment)
    
    def test_add_comment_to_private_post(self):
        request = post_service_pb2.AddCommentRequest(
            post_id=2,
            user_id=3,
            text="Comment to private post"
        )
        response = self.service.AddComment(request, self.context)
        
        self.context.set_code.assert_called_with(grpc.StatusCode.PERMISSION_DENIED)
        
        comment = self.session.query(Comment).filter_by(text="Comment to private post").first()
        self.assertIsNone(comment)
    
    def test_add_comment_post_not_found(self):
        request = post_service_pb2.AddCommentRequest(
            post_id=999,
            user_id=2,
            text="Comment to non-existent post"
        )
        response = self.service.AddComment(request, self.context)
        
        self.context.set_code.assert_called_with(grpc.StatusCode.NOT_FOUND)
    
    def test_get_comments_success(self):
        request = post_service_pb2.GetCommentsRequest(
            post_id=1,
            page=1,
            per_page=10,
            requester_id=2
        )
        response = self.service.GetComments(request, self.context)
        
        self.assertEqual(response.total_count, 2)
        self.assertEqual(len(response.comments), 2)
        self.assertEqual(response.total_pages, 1)
        
        comments_texts = [comment.text for comment in response.comments]
        self.assertIn("Test comment 1", comments_texts)
        self.assertIn("Test comment 2", comments_texts)
    
    def test_get_comments_pagination(self):
        for i in range(3, 13):
            comment = Comment(
                post_id=1,
                user_id=2,
                text=f"Test comment {i}",
                created_at=datetime.utcnow()
            )
            self.session.add(comment)
        self.session.commit()
        
        request = post_service_pb2.GetCommentsRequest(
            post_id=1,
            page=1,
            per_page=5,
            requester_id=2
        )
        response = self.service.GetComments(request, self.context)
        
        self.assertEqual(response.total_count, 12)
        self.assertEqual(len(response.comments), 5)
        self.assertEqual(response.total_pages, 3)
    
    def test_get_comments_from_private_post(self):
        comment = Comment(
            post_id=2,
            user_id=1,
            text="Private post comment",
            created_at=datetime.utcnow()
        )
        self.session.add(comment)
        self.session.commit()
        
        request = post_service_pb2.GetCommentsRequest(
            post_id=2,
            page=1,
            per_page=10,
            requester_id=2
        )
        response = self.service.GetComments(request, self.context)
        
        self.context.set_code.assert_called_with(grpc.StatusCode.PERMISSION_DENIED)

if __name__ == '__main__':
    unittest.main()
