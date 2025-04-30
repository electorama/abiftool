import warnings
warnings.warn(
    "The irvtally lib name is deprecated in abiflib 0.3.0; new name: abiflib.irv_tally",
    DeprecationWarning,
    stacklevel=2,
)
# re-export everything from the new module
from .irv_tally import *
