import warnings
warnings.warn(
    "The preflib lib name is deprecated in abiflib 0.3.0; new name: abiflib.preflib_fmt",
    DeprecationWarning,
    stacklevel=2,
)
# re-export everything from the new module
from .preflib_fmt import *
