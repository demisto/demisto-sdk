from abc import abstractmethod


class AbstractConverter:
    def __init__(self):
        pass

    @abstractmethod
    def convert_dir(self):
        pass
