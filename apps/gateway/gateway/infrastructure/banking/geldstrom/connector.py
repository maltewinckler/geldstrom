"""Geldstrom-backed implementation of the gateway banking connector."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta

from pydantic import SecretStr

from gateway.application.common import BankUpstreamUnavailableError, InternalError
from gateway.domain.banking_gateway import (
    AccountsResult,
    BalancesResult,
    BankingConnector,
    FinTSInstitute,
    OperationStatus,
    OperationType,
    ResumeResult,
    TanMethodsResult,
    TransactionsResult,
)
from gateway.domain.banking_gateway.value_objects import (
    PresentedBankCredentials,
    RequestedIban,
)
from gateway.infrastructure.banking.geldstrom.mapping import (
    approved_result_payload,
    to_account_dict,
    to_balance_dict,
    to_tan_method,
    to_transaction_list,
)
from gateway.infrastructure.banking.geldstrom.models import (
    GeldstromClient,
    GeldstromClientFactory,
)
from geldstrom.clients.fints3_decoupled import FinTS3ClientDecoupled
from geldstrom.domain import (
    Account,
    BankCredentials,
    BankRoute,
)
from geldstrom.infrastructure.fints.challenge import DecoupledTANPending
from geldstrom.infrastructure.fints.credentials import GatewayCredentials
from geldstrom.infrastructure.fints.exceptions import (
    FinTSClientPINError,
    FinTSClientTemporaryAuthError,
    FinTSConnectionError,
    FinTSDialogError,
    FinTSNoResponseError,
    FinTSSCARequiredError,
    FinTSUnsupportedOperation,
)
from geldstrom.infrastructure.fints.session_snapshot import DecoupledSessionSnapshot

_logger = logging.getLogger(__name__)


class _DefaultGeldstromClientFactory(GeldstromClientFactory):
    def create(
        self,
        credentials: GatewayCredentials,
        session_state=None,
    ) -> GeldstromClient:
        return FinTS3ClientDecoupled.from_gateway_credentials(
            credentials,
            session_state=session_state,
        )


class GeldstromBankingConnector(BankingConnector):
    """Translate gateway banking operations to Geldstrom calls."""

    def __init__(
        self,
        product_key: str,
        *,
        product_version: str,
        client_factory: GeldstromClientFactory | None = None,
    ) -> None:
        self._product_key = product_key
        self._product_version = product_version
        self._client_factory = client_factory or _DefaultGeldstromClientFactory()

    async def list_accounts(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> AccountsResult:
        product_key = self._product_key
        return await asyncio.to_thread(
            self._list_accounts_sync,
            institute,
            credentials,
            product_key,
        )

    async def fetch_transactions(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        iban: RequestedIban,
        start_date: date,
        end_date: date,
    ) -> TransactionsResult:
        product_key = self._product_key
        return await asyncio.to_thread(
            self._fetch_transactions_sync,
            institute,
            credentials,
            iban,
            start_date,
            end_date,
            product_key,
        )

    async def get_balances(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> BalancesResult:
        product_key = self._product_key
        return await asyncio.to_thread(
            self._get_balances_sync,
            institute,
            credentials,
            product_key,
        )

    async def get_tan_methods(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> TanMethodsResult:
        product_key = self._product_key
        return await asyncio.to_thread(
            self._get_tan_methods_sync,
            institute,
            credentials,
            product_key,
        )

    async def resume_operation(
        self,
        session_state: bytes,
        credentials: PresentedBankCredentials,
        institute: FinTSInstitute,
    ) -> ResumeResult:
        product_key = self._product_key
        return await asyncio.to_thread(
            self._resume_operation_sync,
            session_state,
            credentials,
            institute,
            product_key,
        )

    def _list_accounts_sync(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        product_key: str,
    ) -> AccountsResult:
        client = self._build_client(institute, credentials, product_key)
        try:
            accounts = client.list_accounts()
        except DecoupledTANPending:
            return self._snapshot_pending(client, AccountsResult)
        return AccountsResult(
            status=OperationStatus.COMPLETED,
            accounts=[to_account_dict(a) for a in accounts],
        )

    def _fetch_transactions_sync(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        iban: RequestedIban,
        start_date: date,
        end_date: date,
        product_key: str,
    ) -> TransactionsResult:
        client = self._build_client(institute, credentials, product_key)
        try:
            account = self._find_account_by_iban(client.list_accounts(), iban)
            if account is None:
                return TransactionsResult(
                    status=OperationStatus.FAILED,
                    failure_reason=f"No account found for IBAN {iban.value}",
                )
            feed = client.get_transactions(
                account, start_date=start_date, end_date=end_date
            )
        except DecoupledTANPending:
            # The TAN may have been triggered by list_accounts() before we
            # even reached get_transactions(). The client's internal snapshot
            # records operation_type='accounts' in that case, so we patch it
            # here to 'transactions' and embed the IBAN + date range so the
            # poll handler can fetch the right data after TAN approval.
            return self._snapshot_transactions_pending(
                client, iban, start_date, end_date
            )
        return TransactionsResult(
            status=OperationStatus.COMPLETED,
            transactions=to_transaction_list(feed),
        )

    def _get_balances_sync(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        product_key: str,
    ) -> BalancesResult:
        client = self._build_client(institute, credentials, product_key)
        try:
            balances = client.get_balances()
        except DecoupledTANPending:
            return self._snapshot_pending(client, BalancesResult)
        return BalancesResult(
            status=OperationStatus.COMPLETED,
            balances=[to_balance_dict(b) for b in balances],
        )

    def _get_tan_methods_sync(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        product_key: str,
    ) -> TanMethodsResult:
        client = self._build_client(institute, credentials, product_key)
        try:
            methods = client.get_tan_methods()
        except DecoupledTANPending:
            return self._snapshot_pending(client, TanMethodsResult)
        return TanMethodsResult(
            status=OperationStatus.COMPLETED,
            methods=[to_tan_method(m) for m in methods],
        )

    def _snapshot_pending(self, client: FinTS3ClientDecoupled, result_cls: type):
        """Serialize the pending TAN state and return a PENDING result."""
        session_state = client.snapshot_pending()
        expires_at = datetime.now(UTC) + timedelta(minutes=5)
        return result_cls(
            status=OperationStatus.PENDING_CONFIRMATION,
            session_state=session_state,
            expires_at=expires_at,
        )

    def _snapshot_transactions_pending(
        self,
        client: FinTS3ClientDecoupled,
        iban: RequestedIban,
        start_date: date,
        end_date: date,
    ) -> TransactionsResult:
        """Snapshot pending TAN state, ensuring operation_type is 'transactions'.

        Two distinct bank behaviours trigger this path:

        * **DKB-style**: ``list_accounts()`` (or ``connect()``) triggers TAN.
          The client snapshot records ``operation_type='accounts'``.  We must
          patch it to ``'transactions'`` and embed the IBAN and date range so
          the poll handler can fetch transactions once the TAN is approved.

        * **Triodos-style**: ``get_transactions()`` itself triggers TAN.
          The client snapshot already records ``operation_type='transactions'``
          and has ``account_id``, ``was_connected=True``, and the date range
          in ``operation_meta``.  Overwriting meta would lose that information,
          forcing an unnecessary second HKKAZ round-trip (and potentially a
          second TAN for wide date ranges).  In this case we return the
          original snapshot unchanged.
        """
        raw = client.snapshot_pending()
        original = DecoupledSessionSnapshot.deserialize(raw)
        expires_at = datetime.now(UTC) + timedelta(minutes=5)

        if original.operation_type == "transactions":
            # TAN was triggered by get_transactions() directly.
            # The snapshot already carries account_id, was_connected=True,
            # and the correct date range - no patching required.
            _logger.debug(
                "_snapshot_transactions_pending: operation_type already 'transactions'; "
                "preserving original snapshot (account_id=%s)",
                original.operation_meta.get("account_id"),
            )
            return TransactionsResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=raw,
                expires_at=expires_at,
            )

        # operation_type is 'accounts' or 'connect' (DKB / HKSPA-first flow).
        # Patch the snapshot so the poll handler knows to fetch transactions.
        _logger.debug(
            "_snapshot_transactions_pending: patching operation_type from '%s' to "
            "'transactions' (iban=%s)",
            original.operation_type,
            iban.value,
        )
        patched = DecoupledSessionSnapshot(
            dialog_snapshot=original.dialog_snapshot,
            task_reference=original.task_reference,
            fints_session_state=original.fints_session_state,
            server_url=original.server_url,
            operation_type="transactions",
            operation_meta={
                "iban": iban.value,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
        )
        return TransactionsResult(
            status=OperationStatus.PENDING_CONFIRMATION,
            session_state=patched.serialize(),
            expires_at=expires_at,
        )

    def _resume_operation_sync(
        self,
        session_state: bytes,
        credentials: PresentedBankCredentials,
        institute: FinTSInstitute,
        product_key: str,
    ) -> ResumeResult:
        client = self._build_client(institute, credentials, product_key)
        result = client.resume_and_poll(session_state)

        if result.status == "pending":
            return ResumeResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=result.data,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
        if result.status == "failed":
            return ResumeResult(
                status=OperationStatus.FAILED,
                failure_reason=result.error or "Unknown error during TAN poll",
            )
        # approved
        op_type = (
            OperationType(result.operation_type) if result.operation_type else None
        )
        return ResumeResult(
            status=OperationStatus.COMPLETED,
            operation_type=op_type,
            result_payload=approved_result_payload(
                result.operation_type or "", result.data
            ),
        )

    def _build_client(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        product_key: str,
        *,
        session_state=None,
    ) -> GeldstromClient:
        gateway_credentials = self._build_gateway_credentials(
            institute, credentials, product_key
        )
        try:
            return self._client_factory.create(
                gateway_credentials, session_state=session_state
            )
        except (
            FinTSClientPINError,
            FinTSClientTemporaryAuthError,
            FinTSSCARequiredError,
            FinTSDialogError,
            FinTSConnectionError,
            FinTSNoResponseError,
            FinTSUnsupportedOperation,
        ) as exc:
            _logger.warning(
                "FinTS bank communication error for %s: %s", institute.blz.value, exc
            )
            raise BankUpstreamUnavailableError("Bank communication failed") from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            raise InternalError(
                "Unexpected failure while creating Geldstrom client"
            ) from exc

    def _build_gateway_credentials(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        product_key: str,
    ) -> GatewayCredentials:
        if institute.pin_tan_url is None:
            raise BankUpstreamUnavailableError(
                f"Institute {institute.blz.value} does not provide a PIN/TAN endpoint"
            )
        if not institute.pin_tan_url.startswith("https://"):
            raise BankUpstreamUnavailableError(
                f"Institute {institute.blz.value} PIN/TAN endpoint is not HTTPS"
            )
        return GatewayCredentials(
            route=BankRoute(country_code="DE", bank_code=institute.blz.value),
            server_url=institute.pin_tan_url,
            credentials=BankCredentials(
                user_id=credentials.user_id.get_secret_value(),
                secret=SecretStr(credentials.password.get_secret_value()),
                two_factor_method=credentials.tan_method,
                two_factor_device=credentials.tan_medium,
            ),
            product_id=product_key,
            product_version=self._product_version,
        )

    @staticmethod
    def _find_account_by_iban(
        accounts: list[Account], iban: RequestedIban
    ) -> Account | None:
        for account in accounts:
            if account.iban == iban.value:
                return account
        return None
