"""Administration command handlers."""

from .create_api_consumer import CreateApiConsumerCommand
from .delete_api_consumer import DeleteApiConsumerCommand
from .disable_api_consumer import DisableApiConsumerCommand
from .rotate_api_consumer_key import RotateApiConsumerKeyCommand
from .sync_institute_catalog import SyncInstituteCatalogCommand
from .update_api_consumer import UpdateApiConsumerCommand
from .update_product_registration import UpdateProductRegistrationCommand

__all__ = [
    "CreateApiConsumerCommand",
    "DeleteApiConsumerCommand",
    "DisableApiConsumerCommand",
    "RotateApiConsumerKeyCommand",
    "SyncInstituteCatalogCommand",
    "UpdateApiConsumerCommand",
    "UpdateProductRegistrationCommand",
]
