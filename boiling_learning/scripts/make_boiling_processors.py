from typing import Dict, List, Union

from boiling_learning.preprocessing.image import (
    ConvertImageDType,
    Cropper,
    Downscaler,
    Grayscaler,
    RandomCropper,
    VideoFrameOrFrames,
)
from boiling_learning.preprocessing.transformers import Operator

ExperimentVideoName = str


def main(
    direct_visualization: bool = True,
    downscale_factor: int = 5,
    direct_height: int = 180,
    indirect_height: int = 108,
    indirect_height_ratio: float = 0.4,
    width: int = 128,
) -> List[
    Union[
        Operator[VideoFrameOrFrames],
        Dict[ExperimentVideoName, Operator[VideoFrameOrFrames]],
    ]
]:
    return [
        ConvertImageDType('float32'),
        Grayscaler(),
        {
            'GOPR2819': Cropper(left=861, right=1687, top=321, bottom=1273),
            'GOPR2820': Cropper(left=861, right=1678, top=321, bottom=1267),
            'GOPR2821': Cropper(left=861, right=1678, top=321, bottom=1267),
            'GOPR2822': Cropper(left=861, right=1678, top=321, bottom=1267),
            'GOPR2823': Cropper(left=861, right=1678, top=321, bottom=1267),
            'GOPR2824': Cropper(left=861, right=1678, top=321, bottom=1267),
            'GOPR2825': Cropper(left=861, right=1678, top=321, bottom=1267),
            'GOPR2826': Cropper(left=861, right=1678, top=321, bottom=1267),
            'GOPR2827': Cropper(left=861, right=1678, top=321, bottom=1267),
            'GOPR2828': Cropper(left=861, right=1678, top=321, bottom=1267),
            'GOPR2829': Cropper(left=861, right=1678, top=321, bottom=1267),
            'GOPR2830': Cropper(left=880, right=1678, top=350, bottom=1267),
            'GOPR2831': Cropper(left=880, right=1678, top=350, bottom=1267),
            'GOPR2832': Cropper(left=880, right=1678, top=350, bottom=1267),
            'GOPR2833': Cropper(left=880, right=1678, top=350, bottom=1267),
            'GOPR2834': Cropper(left=880, right=1678, top=350, bottom=1250),
            'GOPR2835': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2836': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2837': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2838': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2839': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2840': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2841': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2842': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2843': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2844': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2845': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2846': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2847': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2848': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2849': Cropper(left=880, right=1678, top=350, bottom=1260),
            'GOPR2852': Cropper(left=1010, right=1865, top=150, bottom=1240),
            'GOPR2853': Cropper(left=1010, right=1865, top=150, bottom=1240),
            'GOPR2854': Cropper(left=1010, right=1865, top=150, bottom=1240),
            'GOPR2855': Cropper(left=1010, right=1865, top=150, bottom=1240),
            'GOPR2856': Cropper(left=1040, right=1890, top=150, bottom=1240),
            'GOPR2857': Cropper(left=1040, right=1890, top=150, bottom=1240),
            'GOPR2858': Cropper(left=1040, right=1890, top=150, bottom=1240),
            'GOPR2859': Cropper(left=1040, right=1890, top=150, bottom=1240),
            'GOPR2860': Cropper(left=1040, right=1890, top=150, bottom=1240),
            'GOPR2861': Cropper(left=1040, right=1890, top=150, bottom=1240),
            'GOPR2862': Cropper(left=1040, right=1890, top=250, bottom=1240),
            'GOPR2863': Cropper(left=1040, right=1890, top=250, bottom=1240),
            'GOPR2864': Cropper(left=1040, right=1890, top=250, bottom=1240),
            'GOPR2865': Cropper(left=1040, right=1890, top=340, bottom=1240),
            'GOPR2866': Cropper(left=1040, right=1890, top=340, bottom=1240),
            'GOPR2867': Cropper(left=1040, right=1890, top=340, bottom=1240),
            'GOPR2868': Cropper(left=1040, right=1890, top=340, bottom=1240),
            'GOPR2869': Cropper(left=1040, right=1890, top=340, bottom=1240),
            'GOPR2870': Cropper(left=1040, right=1890, top=340, bottom=1240),
            'GOPR2873': Cropper(left=990, right=1780, top=350, bottom=1300),
            'GOPR2874': Cropper(left=990, right=1780, top=350, bottom=1300),
            'GOPR2875': Cropper(left=990, right=1780, top=350, bottom=1300),
            'GOPR2876': Cropper(left=990, right=1780, top=350, bottom=1300),
            'GOPR2877': Cropper(left=990, right=1780, top=350, bottom=1300),
            'GOPR2878': Cropper(left=990, right=1780, top=350, bottom=1300),
            'GOPR2879': Cropper(left=990, right=1780, top=350, bottom=1300),
            'GOPR2880': Cropper(left=990, right=1780, top=350, bottom=1300),
            'GOPR2881': Cropper(left=990, right=1780, top=350, bottom=1300),
            'GOPR2882': Cropper(left=990, right=1780, top=350, bottom=1300),
            'GOPR2884': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2885': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2886': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2887': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2888': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2889': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2890': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2891': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2892': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2893': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2894': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2895': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2896': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2897': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2898': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2899': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2900': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2901': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2902': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2903': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2904': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2905': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2906': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2907': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2908': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2909': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2910': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2911': Cropper(left=960, right=1750, top=450, bottom=1350),
            'GOPR2914': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2915': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2916': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2917': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2918': Cropper(left=960, right=1750, top=400, bottom=1350),
            'GOPR2919': Cropper(left=960, right=1750, top=450, bottom=1350),
            'GOPR2920': Cropper(left=960, right=1750, top=450, bottom=1350),
            'GOPR2921': Cropper(left=960, right=1750, top=450, bottom=1350),
            'GOPR2922': Cropper(left=960, right=1750, top=450, bottom=1350),
            'GOPR2923': Cropper(left=960, right=1750, top=450, bottom=1350),
            'GOPR2925': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2926': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2927': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2928': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2929': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2930': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2931': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2932': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2933': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2934': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2935': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2936': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2937': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2938': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2939': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2940': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2941': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2942': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2943': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2944': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2945': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2946': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2947': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2948': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2949': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2950': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2951': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2952': Cropper(left=980, right=1810, top=300, bottom=1350),
            'GOPR2953': Cropper(left=980, right=1810, top=400, bottom=1350),
            'GOPR2954': Cropper(left=980, right=1810, top=400, bottom=1350),
            'GOPR2955': Cropper(left=980, right=1810, top=400, bottom=1350),
            'GOPR2956': Cropper(left=980, right=1810, top=400, bottom=1350),
            'GOPR2957': Cropper(left=980, right=1810, top=400, bottom=1350),
            'GOPR2959': Cropper(left=980, right=1810, top=400, bottom=1350),
            'GOPR2960': Cropper(left=980, right=1810, top=400, bottom=1350),
        },
        Downscaler(downscale_factor),
        Cropper(
            left=0,
            right_border=0,
            height=(direct_height if direct_visualization else indirect_height),
            bottom_border=(0 if direct_visualization else indirect_height_ratio),
        ),
        RandomCropper(width=width),
    ]


if __name__ == '__main__':
    raise RuntimeError('*make_boiling_processors* cannot be executed as a standalone script yet.')
