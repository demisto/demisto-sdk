from abc import abstractmethod
from typing import Any, Dict


class SingletonMeta(type):
    _instances: Dict[type, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)

        return cls._instances[cls]


class PydanticSingleton:
    _instance = None

    @classmethod
    def get_instance(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = cls.get_instance_from(*args, **kwargs)
        return cls._instance

    @classmethod
    @abstractmethod
    def get_instance_from(cls, *args, **kwargs):
        """
        Pydantic objects should be initialized with class methods and not from the class constructor.
        Each Singleton that is based on pydantic should implement this abstract method.
        """
        pass
