"""Admin CLI command handlers."""

from .create_user import CreateUserCommand
from .delete_user import DeleteUserCommand
from .disable_user import DisableUserCommand
from .reactivate_user import ReactivateUserCommand
from .rotate_user_key import RotateUserKeyCommand
from .sync_institute_catalog import SyncInstituteCatalogCommand
from .update_product_registration import UpdateProductRegistrationCommand
from .update_user import UpdateUserCommand

__all__ = [
    "CreateUserCommand",
    "DeleteUserCommand",
    "DisableUserCommand",
    "ReactivateUserCommand",
    "RotateUserKeyCommand",
    "SyncInstituteCatalogCommand",
    "UpdateProductRegistrationCommand",
    "UpdateUserCommand",
]
