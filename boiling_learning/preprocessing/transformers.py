import operator
from pydoc import describe
from typing import Any, Callable, Generic, Iterator, Mapping, Optional, Tuple, TypeVar, Union

import funcy
from typing_extensions import ParamSpec

from boiling_learning.io import json
from boiling_learning.utils import JSONDataType, KeyedDefaultDict, SimpleStr
from boiling_learning.utils.functional import Pack
from boiling_learning.utils.typeutils import CallableWithFirst

_X = TypeVar('_X')
_X1 = TypeVar('_X1')
_X2 = TypeVar('_X2')
_Y = TypeVar('_Y')
T = TypeVar('T')
_P = ParamSpec('_P')


class Transformer(SimpleStr, Generic[_X, _Y]):
    def __init__(
        self, name: str, f: CallableWithFirst[_X, _P, _Y], pack: Pack[Any, Any] = Pack()
    ) -> None:
        self.__name__: str = name
        self._call = pack.rpartial(f)
        self.pack: Pack[Any, Any] = pack

    @property
    def name(self) -> str:
        return self.__name__

    def __call__(self, arg: _X, *args: Any, **kwargs: Any) -> _Y:
        return self._call(arg, *args, **kwargs)

    def __describe__(self) -> JSONDataType:
        return json.serialize(
            {
                'type': self.__class__.__name__,
                'name': self.name,
                'pack': self.pack,
            }
        )


class FeatureTransformer(Transformer[Tuple[_X1, _Y], Tuple[_X2, _Y]], Generic[_X1, _X2, _Y]):
    def __init__(self, name: str, f: Callable[..., _X2], pack: Pack = Pack()) -> None:
        def g(pair: Tuple[_X1, _Y], *args, **kwargs) -> Tuple[_X2, _Y]:
            feature, target = pair
            return f(feature, *args, **kwargs), target

        super().__init__(name, g, pack=pack)

    def transform_feature(self, feature: _X1, *args, **kwargs) -> _X2:
        return self((feature, None), *args, **kwargs)[0]

    def as_transformer(self) -> Transformer[_X1, _X2]:
        feature_transformer: Transformer[_X1, _X2] = Transformer(self.name, self.transform_feature)
        feature_transformer.pack = self.pack
        return feature_transformer


class KeyedFeatureTransformer(
    Transformer[Tuple[_X1, _Y], Tuple[Union[_X1, _X2], _Y]],
    Generic[_X1, _X2, _Y],
):
    def __init__(
        self,
        name: str,
        f: Callable[..., _X2],
        packer: Union[Callable[[str], Pack], Mapping[Optional[str], Pack]],
        key_getter: Callable[[_Y], Optional[str]] = operator.itemgetter('name'),
    ) -> None:
        self.packer = packer

        def g(pair: Tuple[_X1, _Y], *args, **kwargs) -> Tuple[Union[_X1, _X2], _Y]:
            def mapped_f(feature: _X1, target: _Y) -> Tuple[Union[_X1, _X2], _Y]:
                key = key_getter(target)
                featre_transformer = self.get_feature_transformer(f, key)
                return featre_transformer(feature), target

            return mapped_f(*pair)

        super().__init__(name, g)

    def get_feature_transformer(
        self, f: Callable[..., _X2], key: Optional[str]
    ) -> Callable[[_X1], Union[_X1, _X2]]:
        if callable(self.packer):
            pack = self.packer(key)
            return pack.rpartial(f)

        if key in self.packer:
            return self._get_partial_transformer(f, key)

        if None in self.packer:
            return self._get_partial_transformer(f, None)

        return funcy.identity

    def _get_partial_transformer(
        self, f: Callable[..., _X2], key: Optional[str]
    ) -> Callable[[_X1], _X2]:
        return self.packer[key].rpartial(f)

    def __describe__(self) -> JSONDataType:
        return json.serialize(funcy.merge(super().__describe__(), {'packer': self.packer}))


class DictFeatureTransformer(
    Mapping[str, Transformer[Tuple[_X1, _Y], Tuple[Union[_X1, _X2], _Y]]],
    Generic[_X1, _X2, _Y],
):
    def __init__(
        self,
        name: str,
        f: Callable[..., _X2],
        packer: Union[Callable[[str], Pack], Mapping[Optional[str], Pack]],
    ) -> None:
        self.__name__: str = name
        self.packer: Union[Callable[[str], Pack], Mapping[Optional[str], Pack]] = packer
        self._transformer_mapping: KeyedDefaultDict[
            str, FeatureTransformer[_X1, _X2, _Y]
        ] = KeyedDefaultDict(self._transformer_factory)
        self.func: Callable[..., _X2] = f

    @property
    def name(self) -> str:
        return self.__name__

    def _resolve_func_and_pack(self, key: str) -> Tuple[Callable[[_X1], _X2], Pack]:
        if isinstance(self.packer, Mapping):
            try:
                if key in self.packer:
                    return self.func, self.packer[key]

                pack = self.packer[None]

                return (funcy.identity, Pack()) if pack is None else (self.func, pack)
            except KeyError as e:
                raise KeyError(
                    f'Invalid key {key}: corresponding pack was not found.'
                    ' Define a default pack by passing None: default_pack'
                    ' or None: None to skip missing keys.'
                ) from e

        elif callable(self.packer):
            return self.func, self.packer(key)
        else:
            raise TypeError(
                'self.packer must be either a Mapping[Optional[str], Pack] '
                'or a Callable[[str], Pack]. '
                f'Got {type(self.packer)}'
            )

    def _transformer_factory(self, key: str) -> FeatureTransformer[_X1, _X2, _Y]:
        name = '_'.join((self.name, key))
        func, pack = self._resolve_func_and_pack(key)
        return FeatureTransformer(name, func, pack)

    def __iter__(self) -> Iterator[str]:
        return iter(self._transformer_mapping)

    def __len__(self) -> int:
        return len(self._transformer_mapping)

    def __getitem__(self, key: str) -> FeatureTransformer[_X1, _X2, _Y]:
        return self._transformer_mapping[key]

    def __describe__(self) -> JSONDataType:
        return json.serialize(
            {
                'type': self.__class__.__name__,
                'name': self.name,
                'packer': self.packer
                if isinstance(self.packer, Mapping)
                else self.packer.__name__,
            }
        )


@json.encode.instance(Transformer)
def _encode_transformer(instance: Transformer) -> json.JSONDataType:
    return json.serialize(describe(instance))


@json.encode.instance(DictFeatureTransformer)
def _encode_dict_feature_transformer(instance: DictFeatureTransformer) -> json.JSONDataType:
    return json.serialize(describe(instance))
