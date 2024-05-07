#!/usr/bin/env python3
# abiflib/core.py - core ABIF<=>jabmod conversion functions
#
# Copyright (C) 2023 Rob Lanphier
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
from pprint import pprint
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

    def log(self, msg):
        """Log a message to the file if filehandle is set; otherwise, do nothing."""
        if self._filehandle:
            self._filehandle.write(f"{msg}")
            self._filehandle.flush()

    @classmethod
    def close_file(cls):
        """Closes the file handle if open."""
        if cls._filehandle:
            cls._filehandle.close()
            cls._filehandle = None

def abiflib_test_log(msg=None):
    """Logs to file in ABIFLIB_LOG environment variable if defined."""
    logobj = LogfileSingleton()
    logobj.log(f"{msg}\n")


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
