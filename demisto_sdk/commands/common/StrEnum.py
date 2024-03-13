"""
Create a StrEnum class that works in both python <3.11 and >=3.11
https://tomwojcik.com/posts/2023-01-02/python-311-str-enum-breaking-change
"""

try:
    # On Python3.11, the (backwards incompatible) StrEnum was added. Importing it succesfully means we're on >=3.11.
    from enum import StrEnum  # type:ignore[attr-defined] not available <3.11

except ImportError:
    # If it's not there, we create its equivalent manually.
    from enum import Enum

    class StrEnum(str, Enum):  # type:ignore[no-redef]
        def __str__(self):
            return self
