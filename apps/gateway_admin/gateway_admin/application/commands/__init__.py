"""Admin CLI command handlers."""

from gateway_admin.application.commands.create_user import CreateUserCommand
from gateway_admin.application.commands.delete_user import DeleteUserCommand
from gateway_admin.application.commands.disable_user import DisableUserCommand
from gateway_admin.application.commands.initialize_admin import (
    InitializeDatabaseCommand,
)
from gateway_admin.application.commands.reactivate_user import ReactivateUserCommand
from gateway_admin.application.commands.rotate_user_key import RotateUserKeyCommand
from gateway_admin.application.commands.sync_institute_catalog import (
    SyncInstituteCatalogCommand,
)
from gateway_admin.application.commands.update_product_registration import (
    UpdateProductRegistrationCommand,
)
from gateway_admin.application.commands.update_user import UpdateUserCommand

__all__ = [
    "CreateUserCommand",
    "DeleteUserCommand",
    "DisableUserCommand",
    "InitializeDatabaseCommand",
    "ReactivateUserCommand",
    "RotateUserKeyCommand",
    "SyncInstituteCatalogCommand",
    "UpdateProductRegistrationCommand",
    "UpdateUserCommand",
]
