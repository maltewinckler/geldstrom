"""Helper functions for segment field access compatibility.

This module provides compatibility helpers for accessing segment fields
during the migration from legacy Container-based segments to Pydantic models.
"""
from typing import Any, Type


def get_account_type_for_segment(segment_class: Type[Any]) -> Type[Any] | None:
    """Get the account field type for a segment class.

    Works with both legacy Container-based and Pydantic segments.

    Args:
        segment_class: The segment class to inspect

    Returns:
        The type of the 'account' field, or None if not found

    Example:
        account_type = get_account_type_for_segment(HKSAL6)
        account = account_type.from_wire_list([...])
    """
    # Pydantic segment - use model_fields
    if hasattr(segment_class, 'model_fields'):
        account_field = segment_class.model_fields.get('account')
        if account_field:
            return account_field.annotation
        return None

    # Legacy Container segment - use _fields
    if hasattr(segment_class, '_fields') and 'account' in segment_class._fields:
        return segment_class._fields["account"].type

    return None

