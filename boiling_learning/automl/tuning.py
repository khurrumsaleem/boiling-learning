from typing import List

import tensorflow as tf

from boiling_learning.automl.hypermodels import HyperModel
from boiling_learning.datasets.datasets import DatasetTriplet
from boiling_learning.io import json
from boiling_learning.model.model import Evaluation, ModelArchitecture
from boiling_learning.utils.dataclasses import dataclass
from boiling_learning.utils.described import Described


@dataclass(frozen=True)
class TuneModelParams:
    callbacks: Described[List[tf.keras.callbacks.Callback], json.JSONDataType]
    batch_size: int


@dataclass(frozen=True)
class TuneModelReturn:
    model: ModelArchitecture
    evaluation: Evaluation


def fit_hypermodel(
    hypermodel: HyperModel, datasets: DatasetTriplet[tf.data.Dataset], params: TuneModelParams
) -> ModelArchitecture:
    ds_train, ds_val, _ = datasets

    automodel = hypermodel.automodel
    automodel.fit(
        ds_train,
        validation_data=ds_val,
        callbacks=params.callbacks.value,
        batch_size=params.batch_size,
    )

    model = ModelArchitecture(automodel.export_model())

    return TuneModelReturn(
        model=model,
        evaluation=model.evaluate(ds_val),
    )
