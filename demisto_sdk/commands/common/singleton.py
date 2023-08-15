from demisto_sdk.commands.common.logger import logger

class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            logger.info("creating new singleton")
            cls._instance = super().__new__(cls)
        logger.info("returning existing singleton")
        return cls._instance
