import typer
from pathlib import Path
from typing import Optional
from demisto_sdk.commands.generate_outputs.generate_outputs import run_generate_outputs


def generate_outputs(
    command: Optional[str] = typer.Option(None, "-c", "--command", help="Specific command name (e.g., xdr-get-incidents)"),
    json: Optional[Path] = typer.Option(None, "-j", "--json", help="Valid JSON file path. If not specified, the script will wait for user input in the terminal."),
    prefix: Optional[str] = typer.Option(None, "-p", "--prefix", help="Output prefix like Jira.Ticket, VirusTotal.IP."),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file path. If not specified, it will print to stdout."),
    ai: bool = typer.Option(False, "--ai", help="**Experimental** - Help generate context descriptions via AI transformers."),
    interactive: bool = typer.Option(False, "--interactive", help="Prompt user for descriptions interactively for each output field."),
    descriptions: Optional[Path] = typer.Option(None, "-d", "--descriptions", help="A JSON or a path to a JSON file mapping field names to descriptions."),
    input: Optional[Path] = typer.Option(None, "-i", "--input", help="Valid YAML integration file path."),
    examples: Optional[str] = typer.Option(None, "-e", "--examples", help="Path for file containing command examples."),
    insecure: bool = typer.Option(False, "--insecure", help="Skip certificate validation to run the commands."),
):
    """
    Auto-generates YAML for a command from the JSON result of the relevant API call.
    You can also supply examples files to generate the context description directly in the YAML from those examples.
    """
    # Gather arguments into kwargs dictionary to pass to the function
    kwargs = {
        "command": command,
        "json": json,
        "prefix": prefix,
        "output": output,
        "ai": ai,
        "interactive": interactive,
        "descriptions": descriptions,
        "input": input,
        "examples": examples,
        "insecure": insecure,
    }
    return run_generate_outputs(**kwargs)
