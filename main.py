import datetime
import operator
import os
import sys
from fractions import Fraction
from functools import partial
from pathlib import Path
from typing import (
    Any,
    Callable,
    Container,
    Dict,
    ItemsView,
    Iterable,
    KeysView,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
    ValuesView,
)

import funcy
import more_itertools as mit
import numpy as np
import tensorflow as tf
import tensorflow_addons as tfa
from loguru import logger
from tensorflow.data import AUTOTUNE
from typing_extensions import ParamSpec

from boiling_learning.datasets.bridging import sliceable_dataset_to_tensorflow_dataset
from boiling_learning.datasets.datasets import DatasetSplits, DatasetTriplet
from boiling_learning.datasets.sliceable import (
    SliceableDataset,
    SupervisedSliceableDataset,
    concatenate,
)
from boiling_learning.describe.described import Described
from boiling_learning.io import json
from boiling_learning.io.storage import dataclass, load, save
from boiling_learning.management.allocators import default_table_allocator
from boiling_learning.management.cacher import CachedFunction, Cacher
from boiling_learning.model.callbacks import (
    AdditionalValidationSets,
    BackupAndRestore,
    ReduceLROnPlateau,
    TimePrinter,
)
from boiling_learning.model.definitions import tiny_convnet
from boiling_learning.model.model import Model, ModelArchitecture
from boiling_learning.model.training import (
    CompiledModel,
    CompileModelParams,
    FitModelParams,
    compile_model,
    get_fit_model,
    strategy_scope,
)
from boiling_learning.preprocessing.experiment_video import ExperimentVideo
from boiling_learning.preprocessing.experiment_video_dataset import ExperimentVideoDataset
from boiling_learning.preprocessing.hdf5 import get_frame_from_hdf5, video_to_hdf5
from boiling_learning.preprocessing.transformers import DictTransformer, Transformer
from boiling_learning.preprocessing.video import PimsVideo, VideoFrame
from boiling_learning.scripts import (
    connect_gpus,
    load_cases,
    load_dataset_tree,
    make_boiling_processors,
    make_condensation_processors,
    set_boiling_cases_data,
    set_condensation_datasets_data,
)
from boiling_learning.scripts.utils.initialization import check_all_paths_exist
from boiling_learning.utils.functional import P
from boiling_learning.utils.lazy import Lazy, LazyCallable
from boiling_learning.utils.pathutils import resolve
from boiling_learning.utils.random import random_state
from boiling_learning.utils.typeutils import typename

boiling_learning_path = resolve(os.environ['BOILING_DATA_PATH'])
boiling_experiments_path = boiling_learning_path / 'experiments'
boiling_cases_path = boiling_learning_path / 'cases'
condensation_learning_path = resolve(os.environ['CONDENSATION_DATA_PATH'])
condensation_cases_path = condensation_learning_path / 'data'
analyses_path = boiling_learning_path / 'analyses'
tensorboard_logs_path = resolve(analyses_path / 'models' / 'logs', dir=True)

log_file = resolve(boiling_learning_path / 'logs' / '{time}.log', parents=True)

logger.remove()
logger.add(sys.stderr, level='DEBUG')
logger.add(str(log_file), level='DEBUG')

logger.info('Initializing script')


class Options(NamedTuple):
    test: bool = True
    login_user: bool = False
    convert_videos: bool = True
    pre_load_videos: bool = False
    interact_processed_frames: bool = False
    analyze_downsampling: bool = False
    analyze_consecutive_frames: bool = False
    analyze_learning_curve: bool = True
    analyze_cross_evaluation: bool = True

    def keys(self) -> KeysView[str]:
        return self._asdict().keys()

    def values(self) -> ValuesView[Any]:
        return self._asdict().values()

    def items(self) -> ItemsView[str, Any]:
        return self._asdict().items()


OPTIONS = Options()
logger.info(f'Options: {OPTIONS}')

logger.info('Checking paths')
check_all_paths_exist(
    (
        ('Boiling learning', boiling_learning_path),
        ('Boiling cases', boiling_cases_path),
        ('Boiling experiments', boiling_experiments_path),
        ('Contensation learning', condensation_learning_path),
        ('Contensation cases', condensation_cases_path),
        ('Analyses', analyses_path),
    )
)
logger.info('Succesfully checked paths')

strategy = connect_gpus.main()
strategy_name = typename(strategy)
logger.info(f'Using distribute strategy: {strategy_name}')

boiling_cases_names = tuple(f'case {idx+1}' for idx in range(5))
boiling_cases_names_timed = tuple(funcy.without(boiling_cases_names, 'case 1'))

logger.info('Preparing datasets')
logger.info('Loading cases')
logger.info(f'Loading boiling cases from {boiling_cases_path}')
boiling_cases = LazyCallable(load_cases.main)(
    (boiling_cases_path / case_name for case_name in boiling_cases_names),
    video_suffix='.MP4',
    convert_videos=OPTIONS.convert_videos,
)
boiling_cases_timed = Lazy(
    lambda: tuple(case for case in boiling_cases() if case.name in boiling_cases_names_timed)
)

boiling_experiments_map: Dict[str, Path] = {
    'case 1': boiling_experiments_path / 'Experiment 2020-08-03 16-19' / 'data.csv',
    'case 2': boiling_experiments_path / 'Experiment 2020-08-05 14-15' / 'data.csv',
    'case 3': boiling_experiments_path / 'Experiment 2020-08-05 17-02' / 'data.csv',
    'case 4': boiling_experiments_path / 'Experiment 2020-08-28 15-28' / 'data.csv',
    'case 5': boiling_experiments_path / 'Experiment 2020-09-10 13-53' / 'data.csv',
}

logger.info(f'Loading condensation cases from {condensation_cases_path}')
condensation_datasets = LazyCallable(load_dataset_tree.main)(condensation_cases_path)

logger.info('Setting up video data')
logger.info(f'Setting boiling data from experiments path: {boiling_experiments_path}')
set_boiling_cases_data.main(
    boiling_cases_timed(),
    case_experiment_map=boiling_experiments_map,
    end_frame_index_cache_path=Path('.cache', 'end_frame_index'),
)

condensation_data_path = condensation_cases_path / 'data_spec.yaml'
logger.info(f'Setting condensation data from data path: {condensation_data_path}')
condensation_datasets_merged = set_condensation_datasets_data.main(
    condensation_datasets(),
    condensation_data_path,
    fps_cache_path=Path('.cache', 'fps'),
    end_frame_index_cache_path=Path('.cache', 'end_frame_index'),
)
condensation_datasets_merged_all = ExperimentVideoDataset.make_union(*condensation_datasets_merged)

boiling_preprocessors, boiling_augmentors = make_boiling_processors.main(
    direct_visualization=True,
    downscale_factor=5,
    direct_height=180,
    indirect_height=108,
    indirect_height_ratio=0.4,
    width=128,
)

condensation_preprocessors, condensation_augmentors = make_condensation_processors.main(
    downscale_factor=5, height=8 * 12, width=8 * 12
)


def _compile_transformers_to_video(
    transformers: Iterable[Transformer[VideoFrame, VideoFrame]], video: PimsVideo
) -> List[Transformer[VideoFrame, VideoFrame]]:
    return [
        (
            transformer[video.name] if isinstance(transformer, DictTransformer) else transformer
        ).as_transformer()
        for transformer in transformers
    ]


hdf5_allocator = default_table_allocator(analyses_path / 'datasets' / 'hdf5')


def get_frame(
    index: int,
    video: PimsVideo,
    transformers: Iterable[Transformer[VideoFrame, VideoFrame]],
) -> VideoFrame:
    h5path = hdf5_allocator(P(video, transformers))

    compiled_transformers = tuple(_compile_transformers_to_video(transformers, video))
    if not h5path.exists():
        video_to_hdf5(
            video,
            h5path,
            dataset_name='frames',
            batch_size=1000,
            transformers=compiled_transformers,
        )

    return get_frame_from_hdf5(h5path, index, dataset_name='frames')


if OPTIONS.test:
    sample_ev = mit.first(boiling_cases_timed()[0])
    sample_frame = get_frame(0, sample_ev, boiling_preprocessors)


def sliceable_dataset_from_video_and_transformers(
    video: ExperimentVideo, transformers: Iterable[Transformer[VideoFrame, VideoFrame]]
) -> SupervisedSliceableDataset[VideoFrame, Dict[str, Any]]:
    frame_getter = partial(get_frame, video=video, transformers=list(transformers))

    features = SliceableDataset.from_getitem(frame_getter, length=len(video))
    targets = SliceableDataset.from_sequence(video.targets())
    return SupervisedSliceableDataset.from_features_and_targets(features, targets)


if OPTIONS.test:
    sds = sliceable_dataset_from_video_and_transformers(sample_ev, boiling_preprocessors)
    sample_frame2 = sds[0][0]
    assert np.allclose(sample_frame, sample_frame2)


@dataclass(frozen=True)
class GetImageDatasetParams:
    image_dataset: ExperimentVideoDataset
    transformers: List[Transformer[VideoFrame, VideoFrame]]
    splits: DatasetSplits
    target: Optional[str] = None
    dataset_size: Optional[Union[int, Fraction]] = None


def _get_image_dataset(
    image_dataset: ExperimentVideoDataset,
    transformers: List[Transformer[VideoFrame, VideoFrame]],
    splits: DatasetSplits,
    dataset_size: Optional[Union[int, Fraction]] = None,
    target: Optional[str] = None,
) -> DatasetTriplet[SupervisedSliceableDataset[VideoFrame, Dict[str, Any]]]:
    ds = SupervisedSliceableDataset[VideoFrame, Dict[str, Any]](
        concatenate(
            sliceable_dataset_from_video_and_transformers(video, transformers)
            for video in image_dataset.values()
        )
    )

    if dataset_size is not None:
        ds = ds.take(dataset_size)

    if target is not None:
        ds = ds.map_targets(operator.itemgetter(target))

    with random_state(1997):
        ds_train, ds_val, ds_test = ds.shuffle().split(splits.train, splits.val, splits.test)
    return ds_train, ds_val, ds_test


def get_image_dataset(
    params: GetImageDatasetParams,
) -> DatasetTriplet[SupervisedSliceableDataset[VideoFrame, Dict[str, Any]]]:
    return _get_image_dataset(
        params.image_dataset,
        params.transformers,
        params.splits,
        params.dataset_size,
        target=params.target,
    )


if OPTIONS.test:
    get_image_dataset_params = GetImageDatasetParams(
        boiling_cases_timed()[0],
        transformers=boiling_preprocessors,
        splits=DatasetSplits(
            train=Fraction(70, 100),
            val=Fraction(15, 100),
            test=Fraction(15, 100),
        ),
        dataset_size=Fraction(1, 1000),
        target='Flux [W/cm**2]',
    )
    ds_train, ds_val, ds_test = get_image_dataset(get_image_dataset_params)
    ds_train_len = len(ds_train)
    ds_val_len = len(ds_val)
    ds_test_len = len(ds_test)
    expected_length = sum(len(ev) for ev in boiling_cases_timed()[0]) // 1000
    assert ds_train_len > ds_test_len > 0
    assert (
        ds_train_len + ds_val_len + ds_test_len == expected_length
    ), f'{ds_train_len} + {ds_val_len} + {ds_test_len} != {expected_length}'
    sample_element = ds_train[0]
    assert isinstance(sample_element[0], np.ndarray)
    assert isinstance(sample_element[1], float)


@dataclass(frozen=True)
class AugmentDatasetParams:
    augmentors: Sequence[Transformer[VideoFrame, VideoFrame]]
    take: Optional[Union[int, Fraction]] = None
    augment_train: bool = True
    augment_test: bool = True
    augmentors_to_force: Container[str] = frozenset({'random_cropper'})


def apply_transformers_to_supervised_sliceable_dataset(
    dataset: SupervisedSliceableDataset[VideoFrame, Dict[str, Any]],
    augmentors: Sequence[
        Transformer[Tuple[VideoFrame, Dict[str, Any]], Tuple[VideoFrame, Dict[str, Any]]]
    ],
) -> SupervisedSliceableDataset[VideoFrame, Dict[str, Any]]:
    for augmentor in augmentors:
        dataset = dataset.map(augmentor)
    return dataset


if OPTIONS.test:
    ds_train = apply_transformers_to_supervised_sliceable_dataset(ds_train, boiling_augmentors)
    ds_val = apply_transformers_to_supervised_sliceable_dataset(ds_val, boiling_augmentors)
    ds_test = apply_transformers_to_supervised_sliceable_dataset(ds_test, boiling_augmentors)

    assert len(ds_train) == ds_train_len
    sample_element = ds_train[0]
    assert isinstance(sample_element[0], np.ndarray)
    assert isinstance(sample_element[1], float)


def _augment_datasets(
    datasets: DatasetTriplet[SupervisedSliceableDataset[VideoFrame, Dict[str, Any]]],
    augmentors: Sequence[Transformer[VideoFrame, VideoFrame]],
    take: Optional[Union[int, Fraction]] = None,
    augment_train: bool = True,
    augment_test: bool = True,
    augmentors_to_force: Container[str] = frozenset({'random_cropper'}),
) -> DatasetTriplet[SupervisedSliceableDataset[VideoFrame, Dict[str, Any]]]:
    ds_train, ds_val, ds_test = datasets
    if take is not None:
        ds_train = ds_train.take(take)
        if ds_val is not None:
            ds_val = ds_val.take(take)
        ds_test = ds_test.take(take)

    filtered_augmentors = (
        augmentors
        if augment_test
        else tuple(augmentor for augmentor in augmentors if augmentor.name in augmentors_to_force)
    )
    train_augmentors = augmentors if augment_train else filtered_augmentors
    test_augmentors = augmentors if augment_test else filtered_augmentors

    ds_train = apply_transformers_to_supervised_sliceable_dataset(ds_train, train_augmentors)
    ds_val = apply_transformers_to_supervised_sliceable_dataset(ds_val, test_augmentors)
    ds_test = apply_transformers_to_supervised_sliceable_dataset(ds_test, test_augmentors)

    ds_train = ds_train.shuffle()
    if ds_val is not None:
        ds_val = ds_val.shuffle()
    ds_test = ds_test.shuffle()

    return ds_train, ds_val, ds_test


def augment_datasets(
    datasets: DatasetTriplet[SupervisedSliceableDataset[VideoFrame, Dict[str, Any]]],
    params: AugmentDatasetParams,
) -> DatasetTriplet[SupervisedSliceableDataset[VideoFrame, Dict[str, Any]]]:
    return _augment_datasets(
        datasets,
        augmentors=params.augmentors,
        take=params.take,
        augment_train=params.augment_train,
        augment_test=params.augment_test,
        augmentors_to_force=params.augmentors_to_force,
    )


if OPTIONS.test:
    get_image_dataset_params = GetImageDatasetParams(
        boiling_cases_timed()[0],
        transformers=boiling_preprocessors,
        splits=DatasetSplits(
            train=Fraction(70, 100),
            val=Fraction(15, 100),
            test=Fraction(15, 100),
        ),
        dataset_size=Fraction(1, 10_000),
        target='Flux [W/cm**2]',
    )
    augment_dataset_params = AugmentDatasetParams(augmentors=boiling_augmentors)

    ds_train, ds_val, ds_test = augment_datasets(
        get_image_dataset(get_image_dataset_params),
        augment_dataset_params,
    )

    sample_element = ds_train[0]
    assert isinstance(sample_element[0], np.ndarray)
    assert isinstance(sample_element[1], float)
    sample_frame = sample_element[0]
    path = analyses_path / 'temp' / 'random_frame'
    save(sample_frame, path)
    other_frame = load(path)
    assert np.allclose(sample_frame, other_frame, 1e-8)

    items = ds_train[:4]
    path = analyses_path / 'temp' / 'random_items'
    save(items, path)
    other_items = load(path)

    for (feature1, target1), (feature2, target2) in zip(items, other_items):
        assert np.allclose(feature1, feature2, 1e-8)
        assert target1 == target2

_P = ParamSpec('_P')


class GetFitModel(CachedFunction[_P, Model]):
    def __init__(self, cacher: Cacher[Model]) -> None:
        super().__init__(get_fit_model, cacher)

    def __call__(
        self,
        compiled_model: CompiledModel,
        datasets: Described[DatasetTriplet[SupervisedSliceableDataset], json.JSONDataType],
        params: FitModelParams,
    ) -> Model:
        path = self.allocate('model', compiled_model, datasets, params)
        path = resolve(path, parents=True)

        dataset_cache_path = self.allocate('cache', datasets, params.batch_size)
        dataset_snapshot_path = self.allocate('snapshot', datasets)
        _, ds_val, _ = datasets.value
        ds_val_g10 = sliceable_dataset_to_tensorflow_dataset(ds_val.shuffle()).filter(
            lambda frame, hf: hf >= 10
        )

        if params.batch_size is not None:
            ds_val_g10 = ds_val_g10.batch(params.batch_size)

        ds_val_g10 = ds_val_g10.prefetch(AUTOTUNE)

        params.callbacks.value.extend(
            [
                TimePrinter(),
                tf.keras.callbacks.ModelCheckpoint(
                    filepath=str(path / 'checkpoints' / f'last-trained-{path.name}'),
                    save_best_only=False,
                    monitor='val_loss',
                ),
                BackupAndRestore(path / 'backup', delete_on_end=False),
                AdditionalValidationSets({'HF10': ds_val_g10}, batch_size=params.batch_size),
                tf.keras.callbacks.TensorBoard(
                    tensorboard_logs_path / datetime.datetime.now().strftime('%Y%m%d-%H%M%S'),
                    histogram_freq=1,
                ),
            ]
        )

        creator: Callable[[], Model] = P(
            compiled_model,
            datasets,
            params,
            cache=dataset_cache_path,
            snapshot_path=dataset_snapshot_path,
        ).partial(self.function)

        return self.provide(creator, path)


strategy = Described.from_constructor(tf.distribute.MirroredStrategy, P())

fit_model = GetFitModel(
    Cacher(
        allocator=default_table_allocator(analyses_path / '_temp_trained_models'),
        # exceptions=(FileNotFoundError, NotADirectoryError, tf.errors.OpError)
        exceptions=(FileNotFoundError, NotADirectoryError),
    )
)

if OPTIONS.test:
    logger.info('Training model')

    get_image_dataset_params = GetImageDatasetParams(
        boiling_cases_timed()[0],
        transformers=boiling_preprocessors,
        splits=DatasetSplits(
            train=Fraction(70, 100),
            val=Fraction(15, 100),
            test=Fraction(15, 100),
        ),
        dataset_size=Fraction(1, 1000),
        target='Flux [W/cm**2]',
    )
    augment_dataset_params = AugmentDatasetParams(augmentors=boiling_augmentors)

    ds_train, ds_val, ds_test = augment_datasets(
        get_image_dataset(get_image_dataset_params),
        augment_dataset_params,
    )

    first_frame, _ = ds_train.flatten()[0]

    datasets = Described(
        value=(ds_train, ds_val, ds_test),
        description=(get_image_dataset_params, augment_dataset_params),
    )

    with strategy_scope(strategy):
        architecture = ModelArchitecture(
            tiny_convnet(
                first_frame.shape[:3],
                dropout=0.5,
                hidden_layers_policy='mixed_float16',
                output_layer_policy='float32',
            )
        )
        compile_params = CompileModelParams(
            loss=tf.keras.losses.MeanSquaredError(),
            optimizer=tf.keras.optimizers.Adam(1e-5),
            metrics=[
                tf.keras.metrics.MeanSquaredError('MSE'),
                tf.keras.metrics.RootMeanSquaredError('RMS'),
                tf.keras.metrics.MeanAbsoluteError('MAE'),
                tf.keras.metrics.MeanAbsolutePercentageError('MAPE'),
                tfa.metrics.RSquare('R2', y_shape=(1,)),
            ],
        )
        compiled_model = compile_model(architecture, compile_params)

    fit_model_params = FitModelParams(
        batch_size=1024,
        epochs=3,
        callbacks=Described.from_list(
            [
                Described.from_constructor(tf.keras.callbacks.TerminateOnNaN, P()),
                Described.from_constructor(
                    tf.keras.callbacks.EarlyStopping,
                    P(
                        monitor='val_loss',
                        min_delta=0,
                        patience=10,
                        baseline=None,
                        mode='auto',
                        restore_best_weights=True,
                    ),
                ),
                Described.from_constructor(
                    ReduceLROnPlateau,
                    P(
                        monitor='val_loss',
                        factor=0.5,
                        patience=5,
                        min_delta=0.01,
                        min_delta_mode='relative',
                        min_lr=0,
                        mode='auto',
                        cooldown=2,
                    ),
                ),
            ]
        ),
    )

    # TODO: fix this:
    # model = FitModel(
    #     fit_model(compiled_model, datasets, fit_model_params),
    #     datasets,
    #     compile_params=compiled_model.params,
    #     fit_params=fit_model_params,
    # )


assert False, 'STOP!'

# TODO: use SaveHistory callback?
# TODO: try to convert the dataset type from float64 to float32 or float16 to reduce memory usage
