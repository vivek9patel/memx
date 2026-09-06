from __future__ import annotations

import typer

from memx.cli.datasets_cmd import datasets_app
from memx.cli.debug_cmd import debug
from memx.cli.run_cmd import run

app = typer.Typer(
    name="memx",
    help="Vendor-agnostic diagnostic harness for agentic memory systems.",
    no_args_is_help=True,
)
app.command(name="run")(run)
app.command(name="debug")(debug)
app.add_typer(datasets_app, name="datasets")

if __name__ == "__main__":
    app()
