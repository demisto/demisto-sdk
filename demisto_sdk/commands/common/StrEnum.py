"""
See here
https://tomwojcik.com/posts/2023-01-02/python-311-str-enum-breaking-change
"""

try:
    from enum import StrEnum

    # On Python3.11, the (backwards incompatible) StrEnum was added

except ImportError:
    # For Python<3.11, we have to construct it manually
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self):
            return self.value
