#!/usr/bin/env python3
''' abiflib/devtools.py - Functions/classes for debugging abiftool '''
#
# Copyright (C) 2024 Rob Lanphier
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from abiflib import *
from pprint import pprint, pformat
import copy
import inspect
import json
import os
import re
import sys
import urllib.parse

ABIF_VERSION = "0.1"
ABIF_MODEL_LIMIT = 2500

# "DEBUGARRAY" is a generic array to put debug strings in to get
# printed if there's an exception or other debugging situations
DEBUGARRAY = []

class LogfileSingleton:
    """Either append msgs to ABIFLIB_LOG or quietly munch"""
    _instance = None
    _filename = None
    _filehandle = None
    devtoolmsgs = []

    def __new__(cls, force_log=False):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # If ABIFLIB_LOG isn't set, silently eat all msgs
            if filename := os.getenv('ABIFLIB_LOG'):
                cls._filename = os.getenv('ABIFLIB_LOG')
                if os.path.isabs(filename):
                    logdir = os.path.dirname(filename)
                else:
                    err = f"ABIFLIB_LOG needs to be an absolute path: {filename}"
                    cls.devtoolmsgs.append(err)
                    raise ValueError(err)
                if not os.path.exists(logdir):
                    err = f"Dir in ABIFLIB_LOG path doesn't exist: {logdir}"
                    cls.devtoolmsgs.append(err)
                    raise FileNotFoundError(err)
                cls._filehandle = open(filename, "a")
                msg = f"ABIFLIB_LOG set to {filename}.  "
                msg += "Amending additional debugging output there."
                cls.devtoolmsgs.append(msg)
            elif force_log:
                msg = f"ABIFLIB_LOG isn't set, and {force_log=}"
                raise ValueError(msg)
            else:
                msg = "ABIFLIB_LOG not set, so no extra logging will be done."
                cls.devtoolmsgs.append(msg)
                return cls._instance

        return cls._instance

    def log(self, msg, newline=True, showframeinfo=True, maxfuncnamelen=10,
            maxfilenamelen=10):
        """Log a message to the file if filehandle is set; otherwise, do nothing."""
        from inspect import currentframe, getframeinfo
        callingframeinfo = getframeinfo(currentframe().f_back.f_back)
        linenum = callingframeinfo.lineno
        filename = os.path.basename(callingframeinfo.filename)
        function = callingframeinfo.function
        if maxfuncnamelen and len(function) > maxfuncnamelen:
            function = function[0:maxfuncnamelen] + ".."
        if maxfilenamelen and len(filename) > maxfilenamelen:
            filename = filename[0:maxfilenamelen] + ".."
        if self._filehandle:
            if showframeinfo:
                self._filehandle.write(f"{function} ({filename}:{linenum}): ")
            self._filehandle.write(f"{msg}")
            if newline:
                self._filehandle.write(f"\n")
            self._filehandle.flush()

    def logblob(self, blob, blobmark="BLOB"):
        """Log a pformatted blob to the file if filehandle is set; otherwise, do nothing.

        Set blobmark to None for no markers before/after blob
        """
        if self._filehandle:
            if blobmark:
                self._filehandle.write(f"--{blobmark}START--\n")
            self._filehandle.write(pformat(blob))
            self._filehandle.write(f"\n")
            if blobmark:
                self._filehandle.write(f"--{blobmark}END--\n")
            self._filehandle.flush()

    @classmethod
    def close_file(cls):
        """Closes the file handle if open."""
        if cls._filehandle:
            cls._filehandle.close()
            cls._filehandle = None



def abiflib_test_log(msg=None, newline=True, showframeinfo=True,
                     maxfuncnamelen=10, maxfilenamelen=10):
    """Logs msg to file in ABIFLIB_LOG environment variable if defined."""
    logobj = LogfileSingleton()
    logobj.log(msg, newline, showframeinfo, maxfuncnamelen, maxfilenamelen)


def abiflib_test_logblob(blob, blobmark=None):
    """Logs pformatted blob to file in ABIFLIB_LOG environment variable if defined."""
    logobj = LogfileSingleton()
    logobj.logblob(blob, blobmark)


def abiflib_stackfunc(index=1):
    ''' Return the calling function (as index=1) or indexed function '''
    curframe = inspect.currentframe()
    callstack = inspect.getouterframes(curframe)
    return callstack[index].function


def abiflib_callstackstr(start=1, end=-1):
    ''' Return the calling stack leading to this function '''
    curframe = inspect.currentframe()
    callstack = inspect.getouterframes(curframe)
    stackstr = " < ".join([f.function for f in callstack[start:end]])
    return stackstr


def main():
    """Dev tools for abif (e.g. logging)"""
    parser = argparse.ArgumentParser(
        description='Dev tools for abif (e.g. logging)')
    args = parser.parse_args()

    teststr = "hello werld"
    devobj = LogfileSingleton(force_log=True, verbose=True)
    devobj.log(teststr)


if __name__ == "__main__":
    main()
