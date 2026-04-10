from typing import TypeVar, Generic, Optional, List
from pydantic import BaseModel

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    code: int = 200
    data: Optional[T] = None
    message: str = "success"


class PageParams(BaseModel):
    page: int = 1
    size: int = 20


class PageResult(BaseModel, Generic[T]):
    items: List[T] = []
    total: int = 0
    page: int = 1
    size: int = 20


def ok(data=None, message="success"):
    return Response(code=200, data=data, message=message)


def fail(message="error", code=400):
    return Response(code=code, data=None, message=message)
