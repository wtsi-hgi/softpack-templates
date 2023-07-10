import click
import getpass
import os
import subprocess
import tempfile
import yaml

from pathlib import Path
from typing import Dict, List, Optional, Union

@click.group()
def cli():
    pass

def append_args(args: Optional[List], option: str, value: str):
    args = args or []
    return args + [f"{option}={value}"] if value else args

def add_dict_option(src: Dict, key: str, value: str):
    return {**src, **{key: value}} if value else src

def enlist(arg: Union[str, List]):
    return arg if isinstance(arg, list) else [arg]

def concat_args(args: Union[str, List]):
    return " ".join(enlist(args))

def shell_command(command: str, *args: str):
    args = concat_args([f"'{concat_args(arg)}'" for arg in args])
    return subprocess.run(
        [os.environ["SHELL"], "-c", f"{command} {args}"]
    )

def get_job_name():
    user = getpass.getuser()
    return f"{user}/rstudio-server"

@click.command()
@click.option(
    "--home",
    default=str(Path.cwd()),
    show_default=True,
    metavar="PATH",
    help="home directory inside the container.",
)
@click.option(
    "-M", "memory",
    metavar="MB",
    default=15000,
    show_default=True,
    help="sets the memory limit for the job (in MB).",
)
@click.option(
    "-n", "ntasks",
    metavar="MIN[,MAX]",
    default=str(2),
    show_default=True,
    help="submits a parallel job and specifies the number of tasks in the job.",
)
@click.option(
    "-o", "--output",
    default="rstudio_session.log",
    show_default=True,
    metavar="FILENAME",
    help="output filename.",
)
@click.option(
    "--pwd",
    default=str(Path.cwd()),
    show_default=True,
    metavar="PATH",
    help="initial working directory inside the container.",
)
@click.option(
    "-q", "--queue",
    metavar="QUEUE",
    help="submits the job to the specified queue.",
)
@click.option(
    "--r-libs-user",
    metavar="PATH",
    help="specifies additional directories for R packages.",
)
def start(
    home: str,
    memory: int,
    ntasks: str,
    pwd: str,
    output: str,
    queue: str,
    r_libs_user: str
):
    """Start RStudio server."""
    resource = f"select[model==Intel_Platinum && mem>{memory}] rusage[tmp=5000, mem={memory}] span[hosts=1]"

    properties = { "jobName": get_job_name() }
    properties = add_dict_option(properties, "queueName", queue)

    bsub_options = {
        "properties": properties,
        "io": {
            "errorAppendFile": output,
            "outputAppendFile": output,
        },
        "limit": {
            "memLimit": memory,
        },
        "resource": {
            "numTasks": ntasks,
            "resReq": resource
        }
    }

    bsub_config = tempfile.NamedTemporaryFile(mode='w', delete=False)
    yaml.safe_dump(bsub_options, bsub_config, indent=2, default_flow_style=False)
    bsub_config.close()

    singularity_args = append_args(None, "--home", home)
    singularity_args = append_args(singularity_args, "--pwd", pwd)

    libs = [r_libs_user, "/opt/view/rlib/R/library"]
    libs = filter(lambda lib: lib, libs)
    rsession_options = append_args(None, "r-libs-user", ":".join(libs))

    return shell_command(
        "__rstudio_start",
        output,
        bsub_config.name,
        singularity_args,
        rsession_options
    )


@click.command()
def stop():
    """Stop RStudio server."""
    return shell_command("__rstudio_stop", get_job_name())

@click.command(name="list")
def list_servers():
    """List running RStudio servers."""
    return shell_command("__rstudio_list", get_job_name())

cli.add_command(start)
cli.add_command(stop)
cli.add_command(list_servers)

cli(prog_name="rstudio")
