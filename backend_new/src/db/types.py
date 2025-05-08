from typing import (
    Any,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import JSON, TypeDecorator

Base = declarative_base()

T = TypeVar("T", bound=BaseModel)


class PydanticType(TypeDecorator, Generic[T]):
    """SQLAlchemy type for storing Pydantic models in a database.

    This type can handle both single Pydantic models and lists of Pydantic models.

    Usage:
        # For a single Pydantic model
        field: Mapped[MyModel] = mapped_column(PydanticType(MyModel))

        # For a list of Pydantic models
        field: Mapped[List[MyModel]] = mapped_column(PydanticType(List[MyModel]))
    """

    impl = JSON
    cache_ok = True

    def __init__(self, python_type: Type[T], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._python_type = python_type

        # Check if the type is a List[T]
        origin = get_origin(python_type)
        if origin is list or origin is List:
            self.is_list = True
            self.item_type = get_args(python_type)[0]
        else:
            self.is_list = False
            self.item_type = python_type

    @property
    def python_type(self):
        return self._python_type

    def process_bind_param(self, value: Optional[Union[T, List[T]]], dialect):
        if value is None:
            return None

        if self.is_list:
            return [item.model_dump() for item in value]
        else:
            return value.model_dump()

    def process_result_value(self, value: Any, dialect):
        if value is None:
            return None

        if self.is_list:
            return [self.item_type.model_validate(item) for item in value]
        else:
            return self.item_type.model_validate(value)
