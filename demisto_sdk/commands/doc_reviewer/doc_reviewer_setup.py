import typer

from demisto_sdk.commands.common.logger import logging_setup_decorator
from demisto_sdk.commands.doc_reviewer.doc_reviewer import DocReviewer


@logging_setup_decorator
def doc_review(
    ctx: typer.Context,
    input: list[str] = typer.Option(
        None, "-i", "--input", help="The path to the file to check"
    ),
    no_camel_case: bool = typer.Option(
        False, "--no-camel-case", help="Whether to check CamelCase words"
    ),
    known_words: list[str] = typer.Option(
        None,
        "--known-words",
        help="The path to a file containing additional known words",
    ),
    always_true: bool = typer.Option(
        False,
        "--always-true",
        help="Whether to fail the command if misspelled words are found",
    ),
    expand_dictionary: bool = typer.Option(
        False,
        "--expand-dictionary",
        help="Whether to expand the base dictionary to include more words - will download 'brown' corpus from nltk package",
    ),
    templates: bool = typer.Option(
        False, "--templates", help="Whether to print release notes templates"
    ),
    use_git: bool = typer.Option(
        False,
        "-g",
        "--use-git",
        help="Use git to identify the relevant changed files, will be used by default if '-i' and '--templates' are not set",
    ),
    prev_ver: str = typer.Option(
        None,
        "--prev-ver",
        help="The branch against which changes will be detected if '-g' flag is set. Default is 'demisto/master'",
    ),
    release_notes: bool = typer.Option(
        False, "-rn", "--release-notes", help="Will run only on release notes files"
    ),
    xsoar_only: bool = typer.Option(
        False,
        "-xs",
        "--xsoar-only",
        help="Run only on files from XSOAR-supported Packs.",
    ),
    use_packs_known_words: bool = typer.Option(
        True,
        "-pkw/-spkw",
        "--use-packs-known-words/--skip-packs-known-words",
        help="Will find and load the known_words file from the pack. To use this option make sure you are running from the content directory.",
    ),
    console_log_threshold: str = typer.Option(
        None,
        "--console-log-threshold",
        help="Minimum logging threshold for console output. Possible values: DEBUG, INFO, SUCCESS, WARNING, ERROR.",
    ),
    file_log_threshold: str = typer.Option(
        None, "--file-log-threshold", help="Minimum logging threshold for file output."
    ),
    log_file_path: str = typer.Option(
        None, "--log-file-path", help="Path to save log files."
    ),
):
    """
    Check the spelling in .md and .yml files as well as review release notes.

    **Use-Cases**
     - Used to check for misspelled words in .md files such as README and integration descriptions also in .yml file such as integrations, scripts and playbooks.
     - Performs a basic documentation review on release notes.
    """
    doc_reviewer = DocReviewer(
        file_paths=input,
        known_words_file_paths=known_words,
        no_camel_case=no_camel_case,
        no_failure=always_true,
        expand_dictionary=expand_dictionary,
        templates=templates,
        use_git=use_git,
        prev_ver=prev_ver,
        release_notes_only=release_notes,
        xsoar_only=xsoar_only,
        load_known_words_from_pack=use_packs_known_words,
    )
    result = doc_reviewer.run_doc_review()
    if result:
        raise typer.Exit(0)
    raise typer.Exit(1)
