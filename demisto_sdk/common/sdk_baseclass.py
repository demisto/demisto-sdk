from abc import ABC, abstractmethod


class SDKClass(ABC):

    @staticmethod
    @abstractmethod
    def add_sub_parser(subparsers):
        parser = subparsers.add_parser(
            help='A demisto-sdk class should have a CLI defined and yet none was created for this class'
        )