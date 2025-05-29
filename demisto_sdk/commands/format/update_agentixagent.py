from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML


class AgentixAgentFormat(BaseUpdateYML):
    """AgentixActionFormat class is designed to update AgentixAction YML file according to Demisto's convention.

    Attributes:
        input (str): the path to the file we are updating at the moment.
        output (str): the desired file name to save the updated version of the YML to.
    """

    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
        from_version: str = "",
        no_validate: bool = False,
        update_docker: bool = False,
        add_tests: bool = False,
        clear_cache: bool = False,
        **kwargs,
    ):
        super().__init__(
            input,
            output,
            path,
            from_version,
            no_validate,
            add_tests=add_tests,
            clear_cache=clear_cache,
            **kwargs,
        )
