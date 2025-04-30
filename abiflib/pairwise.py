import warnings
warnings.warn(
    "The pairwise lib name is deprecated in abiflib 0.3.0; new name: abiflib.pairwise_tally",
    DeprecationWarning,
    stacklevel=2,
)
# re-export everything from the new module
from .pairwise_tally import *
