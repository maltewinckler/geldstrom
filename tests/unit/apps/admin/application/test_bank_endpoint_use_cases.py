"""Unit tests for the bank_directory use cases."""

from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from admin.application.bank_directory.use_cases import (
    CreateBankEndpoint,
    DeleteBankEndpoint,
    GetBankEndpoint,
    ListBankEndpoints,
    UpdateBankEndpoint,
)
from admin.domain.bank_directory.entities.bank_endpoint import BankEndpoint
from admin.domain.bank_directory.value_objects.banking_protocol import BankingProtocol
from admin.domain.bank_directory.value_objects.protocol_config import FinTSConfig
from admin.domain.exceptions import (
    BankEndpointAlreadyExistsError,
    BankEndpointNotFoundError,
)


class TestCreateBankEndpoint:
    """Tests for CreateBankEndpoint use case."""

    @pytest.fixture
    def mock_bank_endpoint_repo(self) -> AsyncMock:
        """Create a mock BankEndpointRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_endpoint_cache(self) -> AsyncMock:
        """Create a mock EndpointCache."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self,
        mock_bank_endpoint_repo: AsyncMock,
        mock_endpoint_cache: AsyncMock,
    ) -> CreateBankEndpoint:
        """Create a CreateBankEndpoint use case with mock dependencies."""
        return CreateBankEndpoint(
            bank_endpoint_repo=mock_bank_endpoint_repo,
            endpoint_cache=mock_endpoint_cache,
        )

    @pytest.fixture
    def valid_endpoint(self) -> BankEndpoint:
        """Create a valid BankEndpoint for testing."""
        return BankEndpoint(
            bank_code="12345678",
            protocol=BankingProtocol.fints,
            server_url="https://banking.example.com/fints",
            protocol_config=FinTSConfig(
                product_id=SecretStr("test_product_id"),
                product_version="1.0.0",
                country_code="DE",
            ),
            metadata={"name": "Test Bank"},
        )

    @pytest.mark.asyncio
    async def test_happy_path_creates_endpoint(
        self,
        use_case: CreateBankEndpoint,
        mock_bank_endpoint_repo: AsyncMock,
        mock_endpoint_cache: AsyncMock,
        valid_endpoint: BankEndpoint,
    ) -> None:
        """CreateBankEndpoint should create a new endpoint."""
        mock_bank_endpoint_repo.get.return_value = None

        await use_case.execute(valid_endpoint)

        mock_bank_endpoint_repo.save.assert_called_once_with(valid_endpoint)

    @pytest.mark.asyncio
    async def test_happy_path_updates_cache(
        self,
        use_case: CreateBankEndpoint,
        mock_bank_endpoint_repo: AsyncMock,
        mock_endpoint_cache: AsyncMock,
        valid_endpoint: BankEndpoint,
    ) -> None:
        """CreateBankEndpoint should update the cache with the new endpoint."""
        mock_bank_endpoint_repo.get.return_value = None

        await use_case.execute(valid_endpoint)

        mock_endpoint_cache.set.assert_called_once_with(valid_endpoint)

    @pytest.mark.asyncio
    async def test_already_exists_raises_error(
        self,
        use_case: CreateBankEndpoint,
        mock_bank_endpoint_repo: AsyncMock,
        valid_endpoint: BankEndpoint,
    ) -> None:
        """CreateBankEndpoint should raise error if endpoint already exists."""
        mock_bank_endpoint_repo.get.return_value = valid_endpoint

        with pytest.raises(BankEndpointAlreadyExistsError) as exc_info:
            await use_case.execute(valid_endpoint)

        assert valid_endpoint.bank_code in str(exc_info.value)


class TestUpdateBankEndpoint:
    """Tests for UpdateBankEndpoint use case."""

    @pytest.fixture
    def mock_bank_endpoint_repo(self) -> AsyncMock:
        """Create a mock BankEndpointRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_endpoint_cache(self) -> AsyncMock:
        """Create a mock EndpointCache."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self,
        mock_bank_endpoint_repo: AsyncMock,
        mock_endpoint_cache: AsyncMock,
    ) -> UpdateBankEndpoint:
        """Create an UpdateBankEndpoint use case with mock dependencies."""
        return UpdateBankEndpoint(
            bank_endpoint_repo=mock_bank_endpoint_repo,
            endpoint_cache=mock_endpoint_cache,
        )

    @pytest.fixture
    def existing_endpoint(self) -> BankEndpoint:
        """Create an existing BankEndpoint for testing."""
        return BankEndpoint(
            bank_code="12345678",
            protocol=BankingProtocol.fints,
            server_url="https://banking.example.com/fints",
            protocol_config=FinTSConfig(
                product_id=SecretStr("test_product_id"),
                product_version="1.0.0",
                country_code="DE",
            ),
        )

    @pytest.fixture
    def updated_endpoint(self) -> BankEndpoint:
        """Create an updated BankEndpoint for testing."""
        return BankEndpoint(
            bank_code="12345678",
            protocol=BankingProtocol.fints,
            server_url="https://new-banking.example.com/fints",
            protocol_config=FinTSConfig(
                product_id=SecretStr("new_product_id"),
                product_version="2.0.0",
                country_code="DE",
            ),
        )

    @pytest.mark.asyncio
    async def test_happy_path_updates_endpoint(
        self,
        use_case: UpdateBankEndpoint,
        mock_bank_endpoint_repo: AsyncMock,
        mock_endpoint_cache: AsyncMock,
        existing_endpoint: BankEndpoint,
        updated_endpoint: BankEndpoint,
    ) -> None:
        """UpdateBankEndpoint should update an existing endpoint."""
        mock_bank_endpoint_repo.get.return_value = existing_endpoint

        await use_case.execute(updated_endpoint)

        mock_bank_endpoint_repo.update.assert_called_once_with(updated_endpoint)

    @pytest.mark.asyncio
    async def test_happy_path_refreshes_cache(
        self,
        use_case: UpdateBankEndpoint,
        mock_bank_endpoint_repo: AsyncMock,
        mock_endpoint_cache: AsyncMock,
        existing_endpoint: BankEndpoint,
        updated_endpoint: BankEndpoint,
    ) -> None:
        """UpdateBankEndpoint should refresh the cache with the updated endpoint."""
        mock_bank_endpoint_repo.get.return_value = existing_endpoint

        await use_case.execute(updated_endpoint)

        mock_endpoint_cache.set.assert_called_once_with(updated_endpoint)

    @pytest.mark.asyncio
    async def test_not_found_raises_error(
        self,
        use_case: UpdateBankEndpoint,
        mock_bank_endpoint_repo: AsyncMock,
        updated_endpoint: BankEndpoint,
    ) -> None:
        """UpdateBankEndpoint should raise error if endpoint doesn't exist."""
        mock_bank_endpoint_repo.get.return_value = None

        with pytest.raises(BankEndpointNotFoundError) as exc_info:
            await use_case.execute(updated_endpoint)

        assert updated_endpoint.bank_code in str(exc_info.value)


class TestDeleteBankEndpoint:
    """Tests for DeleteBankEndpoint use case."""

    @pytest.fixture
    def mock_bank_endpoint_repo(self) -> AsyncMock:
        """Create a mock BankEndpointRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_endpoint_cache(self) -> AsyncMock:
        """Create a mock EndpointCache."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self,
        mock_bank_endpoint_repo: AsyncMock,
        mock_endpoint_cache: AsyncMock,
    ) -> DeleteBankEndpoint:
        """Create a DeleteBankEndpoint use case with mock dependencies."""
        return DeleteBankEndpoint(
            bank_endpoint_repo=mock_bank_endpoint_repo,
            endpoint_cache=mock_endpoint_cache,
        )

    @pytest.fixture
    def existing_endpoint(self) -> BankEndpoint:
        """Create an existing BankEndpoint for testing."""
        return BankEndpoint(
            bank_code="12345678",
            protocol=BankingProtocol.fints,
            server_url="https://banking.example.com/fints",
            protocol_config=FinTSConfig(
                product_id=SecretStr("test_product_id"),
                product_version="1.0.0",
                country_code="DE",
            ),
        )

    @pytest.mark.asyncio
    async def test_happy_path_deletes_endpoint(
        self,
        use_case: DeleteBankEndpoint,
        mock_bank_endpoint_repo: AsyncMock,
        mock_endpoint_cache: AsyncMock,
        existing_endpoint: BankEndpoint,
    ) -> None:
        """DeleteBankEndpoint should delete an existing endpoint."""
        mock_bank_endpoint_repo.get.return_value = existing_endpoint

        await use_case.execute(existing_endpoint.bank_code)

        mock_bank_endpoint_repo.delete.assert_called_once_with(
            existing_endpoint.bank_code
        )

    @pytest.mark.asyncio
    async def test_happy_path_removes_from_cache(
        self,
        use_case: DeleteBankEndpoint,
        mock_bank_endpoint_repo: AsyncMock,
        mock_endpoint_cache: AsyncMock,
        existing_endpoint: BankEndpoint,
    ) -> None:
        """DeleteBankEndpoint should remove the endpoint from cache."""
        mock_bank_endpoint_repo.get.return_value = existing_endpoint

        await use_case.execute(existing_endpoint.bank_code)

        mock_endpoint_cache.delete.assert_called_once_with(existing_endpoint.bank_code)

    @pytest.mark.asyncio
    async def test_not_found_raises_error(
        self,
        use_case: DeleteBankEndpoint,
        mock_bank_endpoint_repo: AsyncMock,
    ) -> None:
        """DeleteBankEndpoint should raise error if endpoint doesn't exist."""
        mock_bank_endpoint_repo.get.return_value = None
        bank_code = "nonexistent"

        with pytest.raises(BankEndpointNotFoundError) as exc_info:
            await use_case.execute(bank_code)

        assert bank_code in str(exc_info.value)


class TestGetBankEndpoint:
    """Tests for GetBankEndpoint use case."""

    @pytest.fixture
    def mock_bank_endpoint_repo(self) -> AsyncMock:
        """Create a mock BankEndpointRepository."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self,
        mock_bank_endpoint_repo: AsyncMock,
    ) -> GetBankEndpoint:
        """Create a GetBankEndpoint use case with mock dependencies."""
        return GetBankEndpoint(
            bank_endpoint_repo=mock_bank_endpoint_repo,
        )

    @pytest.fixture
    def existing_endpoint(self) -> BankEndpoint:
        """Create an existing BankEndpoint for testing."""
        return BankEndpoint(
            bank_code="12345678",
            protocol=BankingProtocol.fints,
            server_url="https://banking.example.com/fints",
            protocol_config=FinTSConfig(
                product_id=SecretStr("test_product_id"),
                product_version="1.0.0",
                country_code="DE",
            ),
        )

    @pytest.mark.asyncio
    async def test_happy_path_returns_endpoint(
        self,
        use_case: GetBankEndpoint,
        mock_bank_endpoint_repo: AsyncMock,
        existing_endpoint: BankEndpoint,
    ) -> None:
        """GetBankEndpoint should return an existing endpoint."""
        mock_bank_endpoint_repo.get.return_value = existing_endpoint

        result = await use_case.execute(existing_endpoint.bank_code)

        assert result.bank_code == existing_endpoint.bank_code
        assert result.protocol == existing_endpoint.protocol
        assert result.server_url == existing_endpoint.server_url

    @pytest.mark.asyncio
    async def test_returns_redacted_protocol_config(
        self,
        use_case: GetBankEndpoint,
        mock_bank_endpoint_repo: AsyncMock,
        existing_endpoint: BankEndpoint,
    ) -> None:
        """GetBankEndpoint should return endpoint with redacted protocol_config."""
        mock_bank_endpoint_repo.get.return_value = existing_endpoint

        result = await use_case.execute(existing_endpoint.bank_code)

        # Protocol config should be redacted
        assert result.protocol_config.product_id.get_secret_value() == "***REDACTED***"
        assert result.protocol_config.product_version == "***REDACTED***"
        assert result.protocol_config.country_code == "***REDACTED***"

    @pytest.mark.asyncio
    async def test_not_found_raises_error(
        self,
        use_case: GetBankEndpoint,
        mock_bank_endpoint_repo: AsyncMock,
    ) -> None:
        """GetBankEndpoint should raise error if endpoint doesn't exist."""
        mock_bank_endpoint_repo.get.return_value = None
        bank_code = "nonexistent"

        with pytest.raises(BankEndpointNotFoundError) as exc_info:
            await use_case.execute(bank_code)

        assert bank_code in str(exc_info.value)


class TestListBankEndpoints:
    """Tests for ListBankEndpoints use case."""

    @pytest.fixture
    def mock_bank_endpoint_repo(self) -> AsyncMock:
        """Create a mock BankEndpointRepository."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self,
        mock_bank_endpoint_repo: AsyncMock,
    ) -> ListBankEndpoints:
        """Create a ListBankEndpoints use case with mock dependencies."""
        return ListBankEndpoints(
            bank_endpoint_repo=mock_bank_endpoint_repo,
        )

    @pytest.fixture
    def endpoints(self) -> list[BankEndpoint]:
        """Create a list of BankEndpoints for testing."""
        return [
            BankEndpoint(
                bank_code="12345678",
                protocol=BankingProtocol.fints,
                server_url="https://bank1.example.com/fints",
                protocol_config=FinTSConfig(
                    product_id=SecretStr("product_id_1"),
                    product_version="1.0.0",
                    country_code="DE",
                ),
            ),
            BankEndpoint(
                bank_code="87654321",
                protocol=BankingProtocol.fints,
                server_url="https://bank2.example.com/fints",
                protocol_config=FinTSConfig(
                    product_id=SecretStr("product_id_2"),
                    product_version="2.0.0",
                    country_code="AT",
                ),
            ),
        ]

    @pytest.mark.asyncio
    async def test_happy_path_returns_all_endpoints(
        self,
        use_case: ListBankEndpoints,
        mock_bank_endpoint_repo: AsyncMock,
        endpoints: list[BankEndpoint],
    ) -> None:
        """ListBankEndpoints should return all endpoints."""
        mock_bank_endpoint_repo.list_all.return_value = endpoints

        result = await use_case.execute()

        assert len(result) == 2
        assert result[0].bank_code == "12345678"
        assert result[1].bank_code == "87654321"

    @pytest.mark.asyncio
    async def test_returns_redacted_protocol_configs(
        self,
        use_case: ListBankEndpoints,
        mock_bank_endpoint_repo: AsyncMock,
        endpoints: list[BankEndpoint],
    ) -> None:
        """ListBankEndpoints should return endpoints with redacted protocol_configs."""
        mock_bank_endpoint_repo.list_all.return_value = endpoints

        result = await use_case.execute()

        for endpoint in result:
            assert (
                endpoint.protocol_config.product_id.get_secret_value()
                == "***REDACTED***"
            )
            assert endpoint.protocol_config.product_version == "***REDACTED***"
            assert endpoint.protocol_config.country_code == "***REDACTED***"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_endpoints(
        self,
        use_case: ListBankEndpoints,
        mock_bank_endpoint_repo: AsyncMock,
    ) -> None:
        """ListBankEndpoints should return empty list when no endpoints exist."""
        mock_bank_endpoint_repo.list_all.return_value = []

        result = await use_case.execute()

        assert result == []
