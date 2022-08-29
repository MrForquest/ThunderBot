import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm, ForeignKey


class User(SqlAlchemyBase):
    __tablename__ = 'users'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, unique=True)
    real_name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    nickname = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    rgt_id = sqlalchemy.Column(sqlalchemy.Integer, ForeignKey("regiments.id"), default=-1)
    age = sqlalchemy.Column(sqlalchemy.Integer, default=-1)
    prr = sqlalchemy.Column(sqlalchemy.Integer, default=-1)

    def __repr__(self):
        return f"<User> {self.id} {self.nickname}"
