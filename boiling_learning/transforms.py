from fractions import Fraction
from typing import Any, Tuple, TypeVar, Union

from boiling_learning.datasets.datasets import DatasetTriplet
from boiling_learning.datasets.sliceable import SliceableDataset
from boiling_learning.describe.described import Described
from boiling_learning.preprocessing.transformers import wrap_as_partial_transformer

_Dataset = TypeVar('_Dataset', bound=SliceableDataset[Any])


@wrap_as_partial_transformer
def datasets_merger(
    datasets: Tuple[Described[DatasetTriplet[_Dataset], Any], ...]
) -> DatasetTriplet[_Dataset]:
    dataset_triplet = datasets_concatenater()(datasets)
    return dataset_sampler(count=Fraction(1, len(datasets)))(dataset_triplet)


@wrap_as_partial_transformer
def datasets_concatenater(
    datasets: Tuple[Described[DatasetTriplet[_Dataset], Any], ...]
) -> DatasetTriplet[_Dataset]:
    train_datasets = []
    val_datasets = []
    test_datasets = []

    for dataset_triplet in datasets:
        ds_train, ds_val, ds_test = dataset_triplet.value

        train_datasets.append(ds_train)
        val_datasets.append(ds_val)
        test_datasets.append(ds_test)

    train_dataset = SliceableDataset.concatenate(*train_datasets)
    val_dataset = SliceableDataset.concatenate(*val_datasets)
    test_dataset = SliceableDataset.concatenate(*test_datasets)

    return DatasetTriplet(train_dataset, val_dataset, test_dataset)


@wrap_as_partial_transformer
def dataset_sampler(
    dataset_triplet: Union[
        DatasetTriplet[_Dataset],
        Described[DatasetTriplet[_Dataset], Any],
    ],
    count: Union[int, Fraction],
) -> DatasetTriplet[_Dataset]:
    if isinstance(dataset_triplet, Described):
        dataset_triplet = dataset_triplet.value

    return DatasetTriplet(
        dataset_triplet.train.sample(count),
        dataset_triplet.val.sample(count),
        dataset_triplet.test.sample(count),
    )