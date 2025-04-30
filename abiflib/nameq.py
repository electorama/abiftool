import warnings
warnings.warn(
    "The nameq lib name is deprecated in abiflib 0.3.0; new name: abiflib.nameq_fmt",
    DeprecationWarning,
    stacklevel=2,
)
# re-export everything from the new module
from .nameq_fmt import *
