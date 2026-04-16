from sqlalchemy import Column, Integer, String, SmallInteger, DateTime, ForeignKey, JSON, func
from app.database import Base


class Role(Base):
    __tablename__ = "sys_role"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    code = Column(String(50), unique=True)
    permissions = Column(JSON, comment="权限列表")
    created_at = Column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "sys_user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    real_name = Column(String(50))
    role_id = Column(Integer, ForeignKey("sys_role.id"))
    status = Column(SmallInteger, default=1, comment="1启用 0禁用")
    created_at = Column(DateTime, server_default=func.now())
