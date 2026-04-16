"""Admin CLI root application."""

from __future__ import annotations

import typer

from .catalog import app as catalog_app
from .db import app as db_app
from .inspect import app as inspect_app
from .product import app as product_app
from .users import app as users_app

app = typer.Typer(
    name="gw-admin",
    help="Geldstrom gateway administration CLI.",
    no_args_is_help=True,
)

app.add_typer(db_app)
app.add_typer(users_app)
app.add_typer(catalog_app)
app.add_typer(product_app)
app.add_typer(inspect_app)


def main() -> None:
    app()
