import datetime
import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy import orm


class Regiment(SqlAlchemyBase):
    __tablename__ = 'regiments'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    label = sqlalchemy.Column(sqlalchemy.String)

    def __repr__(self):
        return f"<Regiment> {self.id} {self.label}"
