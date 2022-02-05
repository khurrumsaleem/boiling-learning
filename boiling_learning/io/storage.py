from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar, final

from classes import AssociatedType, Supports, typeclass

from boiling_learning.io import json
from boiling_learning.utils.table_dispatch import TableDispatcher
from boiling_learning.utils.utils import PathLike, resolve

# pylint: disable=missing-function-docstring,missing-class-docstring

_T = TypeVar('_T')


@final
class Serializable(AssociatedType):
    ...


class _SerializableMeta(type):
    def __instancecheck__(cls, instance: Any) -> bool:
        return serialize.supports(instance)


class SupportsSerializable(Supports[Serializable], metaclass=_SerializableMeta):
    ...


@typeclass(Serializable)
def serialize(instance: Supports[Serializable], path: Path) -> None:
    '''Serialize object contents.'''


class _DeserializableMeta(type):
    def __instancecheck__(cls, instance: Any) -> bool:
        return instance in deserialize


class SupportsDeserializable(metaclass=_DeserializableMeta):
    ...


deserialize = TableDispatcher()


class Saveable(AssociatedType):
    ...


class _SupportsSaveableMeta(type):
    def __instancecheck__(cls, instance: Any) -> bool:
        return save.supports(instance)


class SupportsSaveable(
    Supports[Saveable],
    metaclass=_SupportsSaveableMeta,
):
    ...


@typeclass(Saveable)
def save(obj: Supports[Saveable], path: PathLike) -> None:
    '''Save objects.'''


@save.instance(delegate=SupportsSerializable)
def _save_serializable(instance: Supports[Serializable], path: PathLike) -> None:
    path = resolve(path, dir=True)

    metadata_path = path / '__boiling_learning_save_meta__.json'
    metadata = {'type': type(instance) if instance is not None else None}
    json.dump(metadata, metadata_path)

    serialize(instance, path / '__data__')


def load(path: PathLike) -> Any:
    path = resolve(path)

    metadata_path = path / '__boiling_learning_save_meta__.json'
    metadata = json.load(metadata_path)

    obj_type = metadata['type']

    return deserialize[obj_type](path / '__data__')