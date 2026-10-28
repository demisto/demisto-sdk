"""Sample: function argument type annotations (W9014)."""


def no_annotation(a):
    return a


def full(a: int, b: str = "x") -> str:
    return b


def partial(a: int, b):
    return b


def method_like(self, a: int):
    return a


def method_unannotated(self, a):
    return a


def cls_first(cls, a: int):
    return a


def varargs(*args, **kwargs):
    return args


def kwonly(*, a):
    return a


def posonly(a, /):
    return a


def no_args():
    return None


def main(a):
    return a


def __init__(self, a):
    return a


class Holder:
    def __init__(self, a):
        self.a = a

    def method(self, a):
        return a

    @staticmethod
    def static(a):
        return a


identity = lambda a: a  # noqa: E731
