import warnings
warnings.warn(
    "The textoutput lib name is deprecated in abiflib 0.3.0; new name: abiflib.text_output",
    DeprecationWarning,
    stacklevel=2,
)
# re-export everything from the new module
from .text_output import *
