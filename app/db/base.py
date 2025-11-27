"""
📄 파일명: base.py
📌 역할: SQLAlchemy Declarative Base 정의 및 메타데이터 관리.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy ORM Base 클래스"""
    pass