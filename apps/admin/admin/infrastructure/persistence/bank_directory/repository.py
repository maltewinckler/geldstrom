"""Repository implementation for the bank_directory bounded context."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.domain.bank_directory.entities.bank_endpoint import BankEndpoint
from admin.domain.bank_directory.ports.services import ConfigEncryptor
from admin.domain.bank_directory.value_objects.banking_protocol import BankingProtocol
from admin.infrastructure.persistence.bank_directory.models import BankEndpointORM


class BankEndpointRepositoryImpl:
    """Implementation of BankEndpointRepository using SQLAlchemy."""

    def __init__(
        self, session: AsyncSession, config_encryptor: ConfigEncryptor
    ) -> None:
        self._session = session
        self._config_encryptor = config_encryptor

    async def get(self, bank_code: str) -> BankEndpoint | None:
        """Get a bank endpoint by bank code."""
        result = await self._session.execute(
            select(BankEndpointORM).where(BankEndpointORM.bank_code == bank_code)
        )
        orm_endpoint = result.scalar_one_or_none()
        if orm_endpoint is None:
            return None
        return self._to_domain(orm_endpoint)

    async def list_all(self) -> list[BankEndpoint]:
        """List all bank endpoints."""
        result = await self._session.execute(select(BankEndpointORM))
        return [
            self._to_domain(orm_endpoint) for orm_endpoint in result.scalars().all()
        ]

    async def save(self, endpoint: BankEndpoint) -> None:
        """Save a new bank endpoint."""
        encrypted_config = self._config_encryptor.encrypt(endpoint.protocol_config)
        orm_endpoint = BankEndpointORM(
            bank_code=endpoint.bank_code,
            protocol=endpoint.protocol.value,
            server_url=endpoint.server_url,
            protocol_config_encrypted=encrypted_config,
            metadata_=endpoint.metadata,
        )
        self._session.add(orm_endpoint)
        await self._session.flush()

    async def update(self, endpoint: BankEndpoint) -> None:
        """Update an existing bank endpoint."""
        result = await self._session.execute(
            select(BankEndpointORM).where(
                BankEndpointORM.bank_code == endpoint.bank_code
            )
        )
        orm_endpoint = result.scalar_one_or_none()
        if orm_endpoint is not None:
            encrypted_config = self._config_encryptor.encrypt(endpoint.protocol_config)
            orm_endpoint.protocol = endpoint.protocol.value
            orm_endpoint.server_url = endpoint.server_url
            orm_endpoint.protocol_config_encrypted = encrypted_config
            orm_endpoint.metadata_ = endpoint.metadata
            await self._session.flush()

    async def delete(self, bank_code: str) -> None:
        """Delete a bank endpoint by bank code."""
        result = await self._session.execute(
            select(BankEndpointORM).where(BankEndpointORM.bank_code == bank_code)
        )
        orm_endpoint = result.scalar_one_or_none()
        if orm_endpoint is not None:
            await self._session.delete(orm_endpoint)
            await self._session.flush()

    def _to_domain(self, orm_endpoint: BankEndpointORM) -> BankEndpoint:
        """Convert ORM model to domain entity."""
        protocol = BankingProtocol(orm_endpoint.protocol)
        decrypted_config = self._config_encryptor.decrypt(
            orm_endpoint.protocol_config_encrypted, protocol
        )
        return BankEndpoint(
            bank_code=orm_endpoint.bank_code,
            protocol=protocol,
            server_url=orm_endpoint.server_url,
            protocol_config=decrypted_config,
            metadata=orm_endpoint.metadata_,
        )
