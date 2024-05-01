"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mprotean` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``protean.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``protean.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""

import subprocess

from enum import Enum
from typing import Optional

import typer

from rich import print
from typing_extensions import Annotated

from protean.cli.docs import app as docs_app
from protean.cli.generate import app as generate_app
from protean.cli.new import new
from protean.cli.shell import shell
from protean.exceptions import NoDomainException
from protean.utils.domain_discovery import derive_domain
from protean.utils import Database
import pkg_resources
# Create the Typer app
#   `no_args_is_help=True` will show the help message when no arguments are passed
app = typer.Typer(no_args_is_help=True)

app.command()(new)
app.command()(shell)
app.add_typer(generate_app, name="generate")
app.add_typer(docs_app, name="docs")


class Category(str, Enum):
    CORE = "CORE"
    EVENTSTORE = "EVENTSTORE"
    DATABASE = "DATABASE"
    FULL = "FULL"


def version_callback(value: bool):
    if value:
        from protean import __version__

        typer.echo(f"Protean {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool, typer.Option(help="Show version information", callback=version_callback)
    ] = False,
):
    """
    Protean CLI
    """


@app.command()
def test(
    category: Annotated[
        Category, typer.Option("-c", "--category", case_sensitive=False)
    ] = Category.CORE
):
    commands = ["pytest", "--cache-clear", "--ignore=tests/support/"]

    match category.value:
        case "EVENTSTORE":
            # Run tests for EventStore adapters
            # FIXME: Add support for auto-fetching supported event stores
            for store in ["MEMORY", "MESSAGE_DB"]:
                print(f"Running tests for EVENTSTORE: {store}...")
                subprocess.call(commands + ["-m", "eventstore", f"--store={store}"])
        case "DATABASE":
            # Run tests for database adapters
            # FIXME: Add support for auto-fetching supported databases
            for db in ["POSTGRESQL", "SQLITE"]:
                print(f"Running tests for DATABASE: {db}...")
                subprocess.call(commands + ["-m", "database", f"--db={db}"])
        case "FULL":
            # Run full suite of tests with coverage
            # FIXME: Add support for auto-fetching supported adapters
            subprocess.call(
                commands
                + [
                    "--slow",
                    "--sqlite",
                    "--postgresql",
                    "--elasticsearch",
                    "--redis",
                    "--message_db",
                    "--cov=protean",
                    "--cov-config",
                    ".coveragerc",
                    "tests",
                ]
            )

            # Test against each supported database
            for db in ["POSTGRESQL", "SQLITE"]:
                print(f"Running tests for DB: {db}...")

                subprocess.call(commands + ["-m", "database", f"--db={db}"])

            for store in ["MESSAGE_DB"]:
                print(f"Running tests for EVENTSTORE: {store}...")
                subprocess.call(commands + ["-m", "eventstore", f"--store={store}"])
        case _:
            print("Running core tests...")
            subprocess.call(commands)


@app.command()
def server(
    domain: Annotated[str, typer.Option("--domain")] = ".",
    test_mode: Annotated[Optional[bool], typer.Option()] = False,
):
    """Run Async Background Server"""
    # FIXME Accept MAX_WORKERS as command-line input as well
    from protean.server import Engine

    domain = derive_domain(domain)
    if not domain:
        raise NoDomainException(
            "Could not locate a Protean domain. You should provide a domain in"
            '"PROTEAN_DOMAIN" environment variable or pass a domain file in options '
            'and a "domain.py" module was not found in the current directory.'
        )

    engine = Engine(domain, test_mode=test_mode)
    engine.run()


def extract_username_password_database_name(uri):
    """Extracts username, password and database name from a URI."""
    if not uri:
        return None, None, None

    uri = uri.split("://")[1]
    user_pass,dbname_string = uri.split("@")

    username,password = user_pass.split(":")
    database_name = dbname_string.split("/")[1]

    return username, password, database_name

from jinja2 import Environment, FileSystemLoader

@main.command()
@click.option("-c", "--file_path")
def generate_dockerfile(file_path):
    """Generate a Dockerfile for the Protean project"""

    domain_path = os.path.realpath(file_path)
    from protean.domain import Domain
    domain = Domain(__file__, "Tests")
    
    docker_dict = {}
    project_name = input("Enter project name: ") or "protean"
    version = input("Enter version: ") or "0.1"
    docker_dict["version"] = version
    docker_dict["services"] = {}
  
    domain = derive_domain(domain_path)
    
    databases = domain.config.get("DATABASES")
    all_databases = databases.keys()
    templates_path = pkg_resources.resource_filename(__name__, 'template')
    env = Environment(loader=FileSystemLoader(templates_path))
    template = env.get_template('docker-template.yml.j2')
    for db in all_databases:
        if databases.get(db).get("DATABASE") == Database.POSTGRESQL.value and docker_dict.get("services").get("db") is None:

            username,password,database_name = extract_username_password_database_name(databases.get(db).get("DATABASE_URI"))
            docker_dict["services"]["db"] = {
                "image": "postgres:latest",
                "environment": {
                    "POSTGRES_USER":username,
                    "POSTGRES_PASSWORD":password,
                    "POSTGRES_DB":database_name,
                },
                "ports": ["5432:5432"],
                "restart":"unless-stopped",
                "container_name": f"{project_name}-db",
                "volumes": ["/var/lib/postgresql/data"],
                "command": ["postgres", "-c", "log_destination=stderr"]
            }
        
        if databases.get(db).get("DATABASE") == Database.ELASTICSEARCH.value and docker_dict.get("services").get("es") is None:
            docker_dict["services"]["es"] = {
                "image": "docker.elastic.co/elasticsearch/elasticsearch:7.10.2",
                "ports": ["9200:9200"],
                "restart":"unless-stopped",
                "container_name": f"{project_name}-es",
                "environment": "ES_JAVA_OPTS=-Xms256m -Xmx512m"
            }
            
            docker_dict["services"]["kibana"] = {
                "image": "docker.elastic.co/kibana/kibana:7.10.2",
                "ports": ["5601:5601"],
                "restart":"unless-stopped",
                "container_name": f"{project_name}-kibana",
                "ELASTICSEARCH_HOSTS": "http://ul_es:9200"
            }
    new_file_path = "docker-compose.yml"
    rendered_content = template.render(services=docker_dict["services"], version=docker_dict["version"])
    with open(new_file_path, 'w') as docker_compose_file:
        docker_compose_file.write(rendered_content)

        

