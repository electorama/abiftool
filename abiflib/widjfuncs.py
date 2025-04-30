import warnings
warnings.warn(
    "The widjfuncs lib name is deprecated in abiflib 0.3.0; replaced with abiflib.widj_fmt",
    DeprecationWarning,
    stacklevel=2,
)
# re-export everything from the new module
from .widj_fmt import *
