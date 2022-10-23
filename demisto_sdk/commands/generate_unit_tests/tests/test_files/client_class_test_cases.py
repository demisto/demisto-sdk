

class BaseClient:
    ...


class FakeClient(BaseClient):
    FAKE_CLASS_VAR = 'so fake'

    def __init__(self, arg1, arg2, arg3):
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
