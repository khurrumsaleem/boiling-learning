from __future__ import annotations

from typing import (
    Callable,
    Generic,
    Iterable,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    overload,
)

from typing_extensions import Protocol

_T = TypeVar('_T')
_U = TypeVar('_U')
_T_co = TypeVar('_T_co', covariant=True)

class SupportsGetItemByIndex(Protocol[_T_co]):
    def __getitem__(self, i: int) -> _T_co: ...

class Slicerator(Generic[_T]):
    @overload
    def __init__(
        self,
        ancestor: Union[Sequence[_T], Slicerator[_T]],
        indices: None = None,
        length: None = None,
        propagate_attrs: Optional[List[str]] = None,
    ) -> None: ...
    @overload
    def __init__(
        self,
        ancestor: SupportsGetItemByIndex[_T],
        indices: Sequence[int],
        length: None = None,
        propagate_attrs: Optional[List[str]] = None,
    ) -> None: ...
    @overload
    def __init__(
        self,
        ancestor: SupportsGetItemByIndex[_T],
        indices: None,
        length: int,
        propagate_attrs: Optional[List[str]] = None,
    ) -> None: ...
    @classmethod
    def from_func(
        cls,
        func: Callable[[int], _U],
        length: int,
        propagate_atters: Optional[List[str]] = None,
    ) -> Slicerator[_U]: ...
    @classmethod
    def from_class(
        cls,
        some_class: Type[Sequence[_U]],
        propagate_attrs: Optional[List[str]] = None,
    ) -> Type[Slicerator[_U]]: ...
    def __repr__(self) -> str: ...
    @property
    def indices(self) -> Iterable[int]: ...
    @overload
    def __getitem__(self, key: int) -> _T: ...
    @overload
    def __getitem__(self, key: Union[slice, Iterable[Union[bool, int]]]) -> Slicerator[_T]: ...
    def __iter__(self) -> Iterable[_T]: ...
    def __len__(self) -> int: ...
