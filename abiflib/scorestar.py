import warnings
warnings.warn(
    "The scorestar lib name is deprecated in abiflib 0.3.0; new name: abiflib.score_star_tally",
    DeprecationWarning,
    stacklevel=2,
)
# re-export everything from the new module
from .score_star_tally import *
