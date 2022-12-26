import typing
from collections.abc import Iterator
from typing import Any, Optional, Union

import autokeras as ak
import keras_tuner as kt
import tensorflow as tf

from boiling_learning.automl.blocks import ImageNormalizationBlock, LayersBlock
from boiling_learning.io import json
from boiling_learning.lazy import Lazy
from boiling_learning.management.allocators import Allocator
from boiling_learning.model.model import ModelArchitecture, anonymize_model_json
from boiling_learning.utils.pathutils import PathLike, resolve


class HyperModel(kt.HyperModel):
    def __init__(self, automodel: ak.AutoModel) -> None:
        self.automodel = automodel

    def get_config(self) -> dict[str, Any]:
        return typing.cast(dict[str, Any], self.automodel.tuner.hypermodel.get_config())

    def __json_encode__(self) -> dict[str, Any]:
        return anonymize_model_json(
            {key: value for key, value in self.get_config().items() if key != 'name'}
        )

    def __describe__(self) -> dict[str, Any]:
        return typing.cast(dict[str, Any], json.encode(self))

    def iter_best_models(self) -> Iterator[ModelArchitecture]:
        tuner = self.automodel.tuner

        return (
            ModelArchitecture(tuner.load_model(trial))
            for trial in tuner.oracle.get_best_trials(
                # a hack to get all possible trials:
                # see how `num_trials` is only used for slicing a list:
                # https://github.com/keras-team/keras-tuner/blob/d559fdd3a33cc5f2a4d58cf59f9636510d5e1c7d/keras_tuner/engine/oracle.py#L397
                num_trials=None
            )
        )


class ImageRegressor(HyperModel):
    def __init__(
        self,
        loss: tf.keras.losses.Loss,
        metrics: list[tf.keras.metrics.Metric],
        normalize_images: Optional[bool] = None,
        augment_images: Optional[bool] = None,
        directory: Union[PathLike, Allocator, None] = None,
        strategy: Optional[Lazy[tf.distribute.Strategy]] = None,
        **kwargs: Any,
    ) -> None:
        if 'overwrite' in kwargs:
            raise TypeError("the argument 'overwrite' is not supported.")

        if 'distribution_strategy' in kwargs:
            raise TypeError("the argument 'distribution_strategy' is not supported.")

        inputs = ak.ImageInput()
        outputs = ak.ImageBlock(normalize=normalize_images, augment=augment_images)(inputs)
        outputs = ak.SpatialReduction()(outputs)
        outputs = ak.DenseBlock()(outputs)
        outputs = ak.RegressionHead(output_dim=1, loss=loss, metrics=metrics)(outputs)

        if isinstance(directory, Allocator):
            directory = directory.allocate(
                self.__class__.__name__,
                loss=loss,
                metrics=metrics,
                normalize_images=normalize_images,
                augment_images=augment_images,
                **kwargs,
            )
        elif directory is not None:
            directory = resolve(directory, parents=True)

        super().__init__(
            ak.AutoModel(
                inputs,
                outputs,
                directory=directory,
                overwrite=directory is None,
                distribution_strategy=strategy() if strategy is not None else None,
                **kwargs,
            )
        )


class ConvImageRegressor(HyperModel):
    def __init__(
        self,
        loss: tf.keras.losses.Loss,
        metrics: list[tf.keras.metrics.Metric],
        normalize_images: Optional[bool] = None,
        directory: Union[PathLike, Allocator, None] = None,
        strategy: Optional[Lazy[tf.distribute.Strategy]] = None,
        **kwargs: Any,
    ) -> None:
        if 'overwrite' in kwargs:
            raise TypeError("the argument 'overwrite' is not supported.")

        if 'distribution_strategy' in kwargs:
            raise TypeError("the argument 'distribution_strategy' is not supported.")

        outputs = inputs = ak.ImageInput()
        outputs = ImageNormalizationBlock(normalize_images)(outputs)
        outputs = ak.ConvBlock()(outputs)
        outputs = ak.SpatialReduction()(outputs)
        outputs = ak.DenseBlock()(outputs)
        outputs = ak.RegressionHead(output_dim=1, loss=loss, metrics=metrics)(outputs)

        if isinstance(directory, Allocator):
            directory = directory.allocate(
                self.__class__.__name__,
                loss=loss,
                metrics=metrics,
                normalize_images=normalize_images,
                **kwargs,
            )
        elif directory is not None:
            directory = resolve(directory, parents=True)

        super().__init__(
            ak.AutoModel(
                inputs,
                outputs,
                directory=directory,
                overwrite=directory is None,
                distribution_strategy=strategy() if strategy is not None else None,
                **kwargs,
            )
        )


class FixedArchitectureImageRegressor(HyperModel):
    def __init__(
        self,
        layers: list[tf.keras.layers.Layer],
        loss: tf.keras.losses.Loss,
        metrics: list[tf.keras.metrics.Metric],
        directory: Union[PathLike, Allocator, None] = None,
        strategy: Optional[Lazy[tf.distribute.Strategy]] = None,
        **kwargs: Any,
    ) -> None:
        if 'overwrite' in kwargs:
            raise TypeError("the argument 'overwrite' is not supported.")

        if 'distribution_strategy' in kwargs:
            raise TypeError("the argument 'distribution_strategy' is not supported.")

        layers_block = LayersBlock(layers)

        inputs = ak.ImageInput()
        outputs = layers_block(inputs)
        outputs = ak.RegressionHead(output_dim=1, loss=loss, metrics=metrics)(outputs)

        if isinstance(directory, Allocator):
            directory = directory.allocate(
                self.__class__.__name__,
                loss=loss,
                metrics=metrics,
                layers=layers_block.get_config(),
                **kwargs,
            )
        elif directory is not None:
            directory = resolve(directory, parents=True)

        super().__init__(
            ak.AutoModel(
                inputs,
                outputs,
                directory=directory,
                overwrite=directory is None,
                distribution_strategy=strategy() if strategy is not None else None,
                **kwargs,
            )
        )
