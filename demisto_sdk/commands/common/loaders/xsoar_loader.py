from abc import ABC


class XSOAR_Loader(ABC):
    def load(self, stream):
        pass

    def dump(self, data, stream, sort_keys=False):
        pass

    def dumps(self, data, sort_keys=False):
        pass
