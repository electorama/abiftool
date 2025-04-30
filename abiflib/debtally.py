import warnings
warnings.warn(
    "The debtally lib name is deprecated in abiflib 0.3.0; new name: abiflib.debvote_fmt",
    DeprecationWarning,
    stacklevel=2,
)
# re-export everything from the new module
from .debvote_fmt import *
