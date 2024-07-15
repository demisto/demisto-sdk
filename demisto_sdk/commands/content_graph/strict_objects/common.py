import pydantic
from pydantic import BaseModel


def create_model(model_name: str, base_models: tuple, **kwargs) -> BaseModel:
    """
    Wrapper for pydantic.create_model so type:ignore[call-overload] appears only once.
    """
    return pydantic.create_model(
        __model_name=model_name, __base__=base_models, **kwargs
    )  # type:ignore[call-overload]
