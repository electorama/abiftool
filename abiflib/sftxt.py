import warnings
warnings.warn(
    "The sftxt lib name is deprecated in abiflib 0.3.0; new name: abiflib.sftxt_fmt",
    DeprecationWarning,
    stacklevel=2,
)
# re-export everything from the new module
from .sftxt_fmt import *
