"""
Create a StrEnum class that works in both python <3.11 and >=3.11
https://tomwojcik.com/posts/2023-01-02/python-311-str-enum-breaking-change
"""

import sys

if sys.version_info >= (3, 11):
    # On Python3.11, the (backwards incompatible) StrEnum was added. Importing it succesfully means we're on >=3.11.
    from enum import (
        StrEnum as _StrEnum,  # type:ignore[attr-defined]  # not available <3.11
    )
    from typing import Self, overload

    class StrEnum(_StrEnum):
        # Since MyPy falsely detects usage of StrEnum as str, (https://github.com/python/mypy/issues/14688), we patch
        @overload
        def __new__(cls, object: object = ...) -> Self:
            ...

        @overload
        def __new__(
            cls, object: object, encoding: str = ..., errors: str = ...
        ) -> Self:
            ...

        def __new__(cls, *values):
            return _StrEnum._new_member_(cls, *values)

else:  # If it's not there, we create its equivalent manually.
    from enum import Enum

    class StrEnum(str, Enum):  # type:ignore[no-redef]
        def __str__(self):
            return self
