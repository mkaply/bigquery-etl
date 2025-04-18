"""bigquery-etl CLI generate command."""

import importlib.util
import sys
import time
from inspect import getmembers
from pathlib import Path

import rich_click as click

from bigquery_etl.cli.utils import is_valid_project, use_cloud_function_option
from bigquery_etl.config import ConfigLoader

SQL_GENERATORS_DIR = "sql_generators"
GENERATE_COMMAND = "generate"
ROOT = Path(__file__).parent.parent.parent


def generate_group(sql_generators_dir):
    """Create the CLI group for the generate command."""
    commands = []

    # import sql_generators module
    spec = importlib.util.spec_from_file_location(
        sql_generators_dir.name, (sql_generators_dir / "__init__.py").absolute()
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["sql_generators"] = module

    for path in sql_generators_dir.iterdir():
        if "__pycache__" in path.parts:
            # Ignore pycache subdirectories
            continue
        if path.is_dir() and (path / "__init__.py").exists():
            # get Python modules for generators
            spec = importlib.util.spec_from_file_location(
                path.name, (path / "__init__.py").absolute()
            )
            # import and execute the module so that we can access
            # methods that are defined in the module
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # find the `generate` click command in the module by
            # iterating through all the members of the module
            members = getmembers(module)
            generate_cmd = [cmd[1] for cmd in members if cmd[0] == GENERATE_COMMAND]
            if len(generate_cmd) > 0:
                if isinstance(generate_cmd[0], click.Command):
                    # rename command to name of query generator
                    cmd = generate_cmd[0]
                    cmd.name = path.name
                    commands.append(cmd)

    # add commands for generating queries to `generate` click group
    return click.Group(
        name="generate", commands=commands, help="Commands for generating SQL queries."
    )


# expose click command group
generate = generate_group(
    Path(
        ConfigLoader.get(
            "default",
            "sql_generators_dir",
            fallback=ConfigLoader.get(
                "default", "sql_generators_dir", fallback=ROOT / SQL_GENERATORS_DIR
            ),
        )
    )
)


@generate.command(help="Run all query generators", name="all")
@click.option(
    "--output-dir",
    "--output_dir",
    help="Output directory generated SQL is written to",
    type=click.Path(file_okay=False),
    default="sql",
)
@click.option(
    "--target-project",
    "--target_project",
    help="GCP project ID",
    default=ConfigLoader.get("default", "project", fallback="moz-fx-data-shared-prod"),
    callback=is_valid_project,
)
@click.option(
    "--ignore",
    "-i",
    help="Do not run the listed SQL generators",
    default=[],
    multiple=True,
)
@use_cloud_function_option
@click.pass_context
def generate_all(ctx, output_dir, target_project, ignore, use_cloud_function):
    """Run all SQL generators."""
    click.echo(f"Generating SQL content in {output_dir}.")
    click.echo(ROOT / SQL_GENERATORS_DIR)

    def generator_command_sort_key(command):
        match command.name:
            # Run `glean_usage` after `stable_views` because both update `dataset_metadata.yaml` files
            # and we want the `glean_usage` updates to take precedence.
            case "stable_views":
                return (1, command.name)
            case "glean_usage":
                return (2, command.name)
            # Run `derived_view_schemas` last in case other SQL generators create derived views.
            case "derived_view_schemas":
                return (4, command.name)
            case _:
                return (3, command.name)

    global_start_time = time.time()
    for cmd in sorted(generate.commands.values(), key=generator_command_sort_key):
        if cmd.name != "all" and cmd.name not in ignore:
            click.echo(
                click.style(
                    f"Running sql generator: {cmd.name}",
                    fg="green",
                )
            )
            step_start_time = time.time()
            ctx.invoke(
                cmd,
                output_dir=output_dir,
                target_project=target_project,
                use_cloud_function=use_cloud_function,
            )
            step_end_time = time.time()
            click.echo(
                click.style(
                    f"sql generator {cmd.name} finished, took {step_end_time - step_start_time}s, "
                    f"total time: {step_end_time - global_start_time}s",
                    fg="green",
                )
            )
