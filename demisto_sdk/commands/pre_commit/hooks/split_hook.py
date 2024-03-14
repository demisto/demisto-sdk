from demisto_sdk.commands.pre_commit.hooks.hook import Hook
from demisto_sdk.commands.pre_commit.pre_commit_context import PreCommitContext


class SplitHook(Hook):
    """
    This class represents a hook which should be split into multiple hooks, any subclass that implements it
    should update the split hooks context with the newly created hooks
    """

    def __init__(
        self,
        hook: dict,
        repo: dict,
        context: PreCommitContext,
    ) -> None:
        super().__init__(hook, repo=repo, context=context)
        self.context.split_hooks[self.original_hook_id] = set()
