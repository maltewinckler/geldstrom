"""Anti-corruption mapping: geldstrom domain objects → gateway wire format."""

from __future__ import annotations

from gateway.domain.banking_gateway import TanMethod
from geldstrom.domain import Account, BalanceSnapshot, TransactionFeed
from geldstrom.infrastructure.fints.tan import TANMethod as GeldstromTanMethod


def to_account_dict(account: Account) -> dict[str, object]:
    return {
        "account_id": account.account_id,
        "iban": account.iban,
        "bic": account.bic,
        "currency": account.currency,
        "product_name": account.product_name,
        "owner_name": account.owner.name if account.owner else None,
        "bank_code": account.bank_route.bank_code,
        "country_code": account.bank_route.country_code,
        "capabilities": dict(account.capabilities.as_dict()),
        "labels": list(account.raw_labels),
        "metadata": dict(account.metadata),
    }


def to_balance_dict(snapshot: BalanceSnapshot) -> dict[str, object]:
    return {
        "account_id": snapshot.account_id,
        "as_of": snapshot.as_of.isoformat(),
        "booked_amount": str(snapshot.booked.amount),
        "booked_currency": snapshot.booked.currency,
        "pending_amount": str(snapshot.pending.amount) if snapshot.pending else None,
        "pending_currency": snapshot.pending.currency if snapshot.pending else None,
        "available_amount": str(snapshot.available.amount)
        if snapshot.available
        else None,
        "available_currency": snapshot.available.currency
        if snapshot.available
        else None,
    }


def to_transaction_list(feed: TransactionFeed) -> list[dict[str, object]]:
    return [
        {
            "transaction_id": entry.entry_id,
            "account_id": feed.account_id,
            "booking_date": entry.booking_date.isoformat(),
            "value_date": entry.value_date.isoformat(),
            "amount": str(entry.amount),
            "currency": entry.currency,
            "purpose": entry.purpose,
            "counterpart_name": entry.counterpart_name,
            "counterpart_iban": entry.counterpart_iban,
            "metadata": dict(entry.metadata),
            "feed_start_date": feed.start_date.isoformat(),
            "feed_end_date": feed.end_date.isoformat(),
            "has_more": feed.has_more,
        }
        for entry in feed.entries
    ]


def to_tan_method(method: GeldstromTanMethod) -> TanMethod:
    return TanMethod(
        method_id=method.code,
        display_name=method.name,
        is_decoupled=method.is_decoupled,
    )


def approved_result_payload(operation_type: str, data: object) -> dict[str, object]:
    """Translate a typed domain result from resume_and_poll into a payload dict."""
    if operation_type in ("accounts", "connect") and data is not None:
        return {"accounts": [to_account_dict(a) for a in data]}  # type: ignore[union-attr]
    if operation_type == "transactions" and isinstance(data, TransactionFeed):
        return {"transactions": to_transaction_list(data)}
    if operation_type in ("balances", "balance") and data is not None:
        if isinstance(data, BalanceSnapshot):
            return {"balances": [to_balance_dict(data)]}
        return {"balances": [to_balance_dict(b) for b in data]}  # type: ignore[union-attr]
    if operation_type == "tan_methods" and data is not None:
        return {"methods": [to_tan_method(m).model_dump() for m in data]}  # type: ignore[union-attr]
    return {}
