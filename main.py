import operator
import os
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
import ray
import tensorflow as tf
import tensorflow_addons as tfa
from tensorflow.data import AUTOTUNE
from tensorflow.keras.layers import (  # Conv2D,; MaxPool2D,
    Activation,
    AveragePooling2D,
    Dense,
    Dropout,
    Flatten,
    Input,
    LayerNormalization,
)
from tensorflow.keras.mixed_precision.experimental import Policy
from typing_extensions import ParamSpec

from boiling_learning.datasets.datasets import DatasetSplits
from boiling_learning.datasets.sliceable import (
    SliceableDataset,
    SupervisedSliceableDataset,
    concatenate,
    sliceable_dataset_to_tensorflow_dataset,
)
from boiling_learning.io import json
from boiling_learning.io.io import DatasetTriplet
from boiling_learning.io.storage import load, save
from boiling_learning.management.allocators import default_table_allocator
from boiling_learning.management.cacher import CachedFunction, Cacher, cache
from boiling_learning.model.callbacks import (
    AdditionalValidationSets,
    ReduceLROnPlateau,
    TimePrinter,
)
from boiling_learning.model.model import Model, ProblemType
from boiling_learning.model.training import (
    CompiledModel,
    CompileModelParams,
    FitModel,
    FitModelParams,
    ModelArchitecture,
    compile_model,
    get_fit_model,
)
from boiling_learning.preprocessing.cases import Case
from boiling_learning.preprocessing.experiment_video import ExperimentVideo
from boiling_learning.preprocessing.image_datasets import ImageDataset
from boiling_learning.preprocessing.transformers import DictFeatureTransformer, Transformer
from boiling_learning.preprocessing.video import Video, VideoFrame
from boiling_learning.scripts import (
    load_cases,
    load_dataset_tree,
    make_boiling_processors,
    make_condensation_processors,
    set_boiling_cases_data,
    set_condensation_datasets_data,
)
from boiling_learning.scripts.utils.initialization import check_all_paths_exist, initialize_gpus
from boiling_learning.utils import enum_item, print_header, resolve
from boiling_learning.utils.dataclasses import dataclass
from boiling_learning.utils.described import Described
from boiling_learning.utils.functional import P
from boiling_learning.utils.lazy import Lazy, LazyCallable
from boiling_learning.utils.typeutils import Many, typename

ray.init(ignore_reinit_error=True)


print_header('Initializing script')


class Options(NamedTuple):
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


print_header('Options', level=1)
OPTIONS = Options()
for option, value in OPTIONS.items():
    print(f'{option}: {value}')

boiling_learning_path: Path = resolve(os.environ['BOILING_DATA_PATH'])
boiling_experiments_path: Path = boiling_learning_path / 'experiments'
boiling_cases_path: Path = boiling_learning_path / 'cases'
condensation_learning_path: Path = resolve(os.environ['CONDENSATION_DATA_PATH'])
condensation_cases_path: Path = condensation_learning_path / 'data'
analyses_path: Path = boiling_learning_path / 'analyses'

print_header('Important paths', level=1)
check_all_paths_exist(
    (
        ('Boiling learning', boiling_learning_path),
        ('Boiling cases', boiling_cases_path),
        ('Boiling experiments', boiling_experiments_path),
        ('Contensation learning', condensation_learning_path),
        ('Contensation cases', condensation_cases_path),
        ('Analyses', analyses_path),
    ),
    verbose=True,
)

print_header('Checking CPUs and GPUs', level=1)
strategy: tf.distribute.Strategy = initialize_gpus()
strategy_name: str = typename(strategy)
print('Using distribute strategy:', strategy_name)

boiling_cases_names: Many[str] = tuple(f'case {idx+1}' for idx in range(2))
# FIXME: use the following:
# boiling_cases_names: Many[str] = tuple(f'case {idx+1}' for idx in range(5))
boiling_cases_names_timed: Many[str] = tuple(funcy.without(boiling_cases_names, 'case 1'))

print_header('Preparing datasets')
print_header('Loading cases', level=1)
print('Loading boiling cases from', boiling_cases_path)
boiling_cases: Lazy[Many[Case]] = LazyCallable(load_cases.main)(
    (boiling_cases_path / case_name for case_name in boiling_cases_names),
    video_suffix='.MP4',
    options=load_cases.Options(
        convert_videos=OPTIONS.convert_videos,
        pre_load_videos=OPTIONS.pre_load_videos,
    ),
    verbose=False,
)
boiling_cases_timed: Lazy[Many[Case]] = Lazy(
    lambda: tuple(case for case in boiling_cases() if case.name in boiling_cases_names_timed)
)

boiling_experiments_map: Dict[str, Path] = {
    'case 1': boiling_experiments_path / 'Experiment 2020-08-03 16-19' / 'data.csv',
    'case 2': boiling_experiments_path / 'Experiment 2020-08-05 14-15' / 'data.csv',
    'case 3': boiling_experiments_path / 'Experiment 2020-08-05 17-02' / 'data.csv',
    'case 4': boiling_experiments_path / 'Experiment 2020-08-28 15-28' / 'data.csv',
    'case 5': boiling_experiments_path / 'Experiment 2020-09-10 13-53' / 'data.csv',
}

print('Loading condensation cases from', condensation_cases_path)
condensation_datasets = LazyCallable(load_dataset_tree.main)(
    condensation_cases_path,
    load_dataset_tree.Options(
        convert_videos=OPTIONS.convert_videos,
        pre_load_videos=OPTIONS.pre_load_videos,
    ),
)

print_header('Setting up video data', level=1)
print('Setting boiling data from experiments path:', boiling_experiments_path)
set_boiling_cases_data.main(
    boiling_cases_timed(),
    case_experiment_map=boiling_experiments_map,
    verbose=True,
)

condensation_data_path = condensation_cases_path / 'data_spec.yaml'
print('Setting condensation data from data path:', condensation_data_path)
condensation_datasets_dict = set_condensation_datasets_data.main(
    condensation_datasets(),
    condensation_data_path,
    verbose=2,
    fps_cache_path=Path('.cache', 'fps'),
)
condensation_all_cases = ImageDataset.make_union(*condensation_datasets_dict.values())

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
    transformers: Iterable[Transformer[VideoFrame, VideoFrame]], video: Video
) -> List[Transformer[VideoFrame, VideoFrame]]:
    return [
        (
            transformer[video.name]
            if isinstance(transformer, DictFeatureTransformer)
            else transformer
        ).as_transformer()
        for transformer in transformers
    ]


@cache(default_table_allocator(analyses_path / 'datasets' / 'frames'))
def get_frame(
    index: int,
    video: Video,
    transformers: Iterable[Transformer[VideoFrame, VideoFrame]],
) -> VideoFrame:
    frame = video[index]
    for transformer in _compile_transformers_to_video(transformers, video):
        frame = transformer(frame)
    return frame


sample_ev = mit.first(boiling_cases_timed()[0])
sample_frame = get_frame(0, sample_ev, boiling_preprocessors)


def sliceable_dataset_from_video_and_transformers(
    video: ExperimentVideo, transformers: Iterable[Transformer[VideoFrame, VideoFrame]]
) -> SupervisedSliceableDataset[VideoFrame, Dict[str, Any]]:
    frame_getter = partial(get_frame, video=video, transformers=list(transformers))

    features = SliceableDataset.from_func(frame_getter, length=len(video))
    targets = SliceableDataset(video.targets())
    return SupervisedSliceableDataset.from_features_and_targets(features, targets)


sds = sliceable_dataset_from_video_and_transformers(sample_ev, boiling_preprocessors)
sample_frame2 = sds[0][0]
assert np.allclose(sample_frame, sample_frame2)


@dataclass(frozen=True)
class GetImageDatasetParams:
    image_dataset: ImageDataset
    transformers: List[Transformer[VideoFrame, VideoFrame]]
    splits: DatasetSplits
    target: Optional[str] = None
    dataset_size: Optional[Union[int, Fraction]] = None


def _get_image_dataset(
    image_dataset: ImageDataset,
    transformers: List[Transformer[VideoFrame, VideoFrame]],
    splits: DatasetSplits,
    dataset_size: Optional[Union[int, Fraction]] = None,
    target: Optional[str] = None,
) -> DatasetTriplet[SupervisedSliceableDataset[VideoFrame, Dict[str, Any]]]:
    ds: SupervisedSliceableDataset[VideoFrame, Dict[str, Any]] = SupervisedSliceableDataset(
        concatenate(
            sliceable_dataset_from_video_and_transformers(video, transformers)
            for video in image_dataset.values()
        )
    )

    if dataset_size is not None:
        ds = ds.take(dataset_size)

    if target is not None:
        ds = ds.map_targets(operator.itemgetter(target))

    dss = ds.shuffle().split(splits.train, splits.val, splits.test)
    assert len(dss) == 3
    return dss


@cache(default_table_allocator(analyses_path / 'datasets' / 'sliceable_image_datasets2'))
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
        path = self.allocate(compiled_model, datasets, params)
        path = resolve(path, parents=True)

        _, ds_val, _ = datasets.value
        ds_val_g10 = (
            sliceable_dataset_to_tensorflow_dataset(ds_val, shuffle=True)
            .filter(lambda frame, hf: hf >= 10)
            .take(
                # the following quantity is defined on
                # "Visualization-based nucleate boiling heat flux quantification
                # using machine learning"
                12614
            )
        )

        if params.batch_size is not None:
            ds_val_g10 = ds_val_g10.batch(params.batch_size)

        ds_val_g10 = ds_val_g10.prefetch(AUTOTUNE)

        params.callbacks.value.extend(
            [
                TimePrinter(),
                tf.keras.callbacks.ModelCheckpoint(
                    filepath=str(path.parent / f'last-trained-{path.name}'),
                    save_best_only=False,
                    monitor='val_loss',
                ),
                tf.keras.callbacks.BackupAndRestore(str(path.parent / f'backup-{path.name}')),
                AdditionalValidationSets(
                    [(ds_val_g10, 'HF10')], batch_size=params.batch_size, verbose=1
                ),
            ]
        )

        creator: Callable[[], Model] = P(compiled_model, datasets, params).partial(self.function)

        return self.provide(creator, path)


_get_fit_model = GetFitModel(
    Cacher(allocator=default_table_allocator(analyses_path / 'models' / 'trained_models4'))
)


def fit_model(
    architecture: ModelArchitecture,
    compile_params: CompileModelParams,
    fit_model_params: FitModelParams,
    image_dataset_get_params: GetImageDatasetParams,
    image_dataset_augment_params: AugmentDatasetParams,
) -> FitModel:
    datasets = Described(
        value=augment_datasets(
            get_image_dataset(image_dataset_get_params), image_dataset_augment_params
        ),
        description=(image_dataset_get_params, image_dataset_augment_params),
    )
    compiled_model = compile_model(architecture, compile_params)
    model = _get_fit_model(compiled_model, datasets, fit_model_params)
    return FitModel(
        model, datasets, compile_params=compiled_model.params, fit_params=fit_model_params
    )


def small_convnet(
    input_shape: Union[Tuple[int, int, int], Tuple[int, int]],
    dropout: Optional[float],
    hidden_layers_policy: Union[str, Policy],
    output_layer_policy: Union[str, Policy],
    problem: Union[int, str, ProblemType] = ProblemType.REGRESSION,
    num_classes: Optional[int] = None,
    normalize_images: bool = False,
) -> ModelArchitecture:
    if len(input_shape) == 2:
        input_shape = input_shape + (1,)

    input_data = Input(shape=input_shape)
    x = input_data  # start "current layer" as the input layer

    x = AveragePooling2D((10, 10))(x)

    if normalize_images:
        x = LayerNormalization()(x)
    # x = Conv2D(
    #     16,
    #     (5, 5),
    #     padding='same',
    #     activation='relu',
    #     dtype=hidden_layers_policy,
    # )(x)
    # x = MaxPool2D((2, 2), strides=(2, 2), dtype=hidden_layers_policy)(x)
    x = Dropout(dropout, dtype=hidden_layers_policy)(x)
    x = Flatten(dtype=hidden_layers_policy)(x)
    # x = Dense(32, activation='relu', dtype=hidden_layers_policy)(x)
    # x = Dropout(dropout, dtype=hidden_layers_policy)(x)

    problem = enum_item(ProblemType, problem)
    if problem is ProblemType.CLASSIFICATION:
        x = Dense(num_classes, dtype=hidden_layers_policy)(x)
        predictions = Activation('softmax', dtype=output_layer_policy)(x)
    elif problem is ProblemType.REGRESSION:
        x = Dense(1, dtype=hidden_layers_policy)(x)
        predictions = Activation('linear', dtype=output_layer_policy)(x)
    else:
        raise ValueError(f'unknown problem type: \"{problem}\"')

    return ModelArchitecture(Model(inputs=input_data, outputs=predictions))


first_frame = ds_train.flatten()[0][0]


model = fit_model(
    architecture=small_convnet(
        first_frame.shape[:3],
        dropout=0.5,
        hidden_layers_policy='mixed_float16',
        output_layer_policy='float32',
    ),
    compile_params=CompileModelParams(
        loss=tf.keras.losses.MeanSquaredError(),
        optimizer=tf.keras.optimizers.Adam(1e-5),
        metrics=[
            tf.keras.metrics.MeanSquaredError('MSE'),
            tf.keras.metrics.RootMeanSquaredError('RMS'),
            tf.keras.metrics.MeanAbsoluteError('MAE'),
            tf.keras.metrics.MeanAbsolutePercentageError('MAPE'),
            tfa.metrics.RSquare('R2', y_shape=(1,)),
        ],
    ),
    fit_model_params=FitModelParams(
        batch_size=128,
        epochs=100,
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
    ),
    image_dataset_get_params=get_image_dataset_params,
    image_dataset_augment_params=augment_dataset_params,
)

assert False, 'STOP!'

# TODO: use SaveHistory callback?
# TODO: try to convert the dataset type from float64 to float32 or float16 to reduce memory usage
