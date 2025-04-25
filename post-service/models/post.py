from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Table,
    ForeignKey,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/posts")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

Base = declarative_base()

post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id")),
    Column("tag_id", Integer, ForeignKey("tags.id")),
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=False)
    creator_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_private = Column(Boolean, default=False)

    tags = relationship("Tag", secondary=post_tags, backref="posts")


def create_tables():
    Base.metadata.create_all(engine)
