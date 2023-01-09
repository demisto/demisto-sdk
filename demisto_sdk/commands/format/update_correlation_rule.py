from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML


class CorrelationRuleYMLFormat(BaseUpdateYML):
    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
        from_version: str = "",
        no_validate: bool = False,
        verbose: bool = False,
        **kwargs,
    ):
        super().__init__(
            input=input,
            output=output,
            path=path,
            from_version=from_version,
            no_validate=no_validate,
            verbose=verbose,
            **kwargs,
        )
        if isinstance(self.data, list) and len(self.data) == 1:
            self.data = self.data[0]
