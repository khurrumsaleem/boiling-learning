from typing import Iterable

from boiling_learning.preprocessing.cases import Case
from boiling_learning.utils.pathutils import PathLike


def main(
    casepaths: Iterable[PathLike], video_suffix: str, convert_videos: bool = False
) -> tuple[Case, ...]:
    cases = tuple(Case(casepath, video_suffix=video_suffix) for casepath in casepaths)

    if convert_videos:
        for case in cases:
            case.convert_videos('.mp4', 'converted', overwrite=False)

    return cases


if __name__ == '__main__':
    raise RuntimeError('*load_cases* cannot be executed as a standalone script yet.')
