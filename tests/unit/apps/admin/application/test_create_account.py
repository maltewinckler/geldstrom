"""Unit tests for the CreateAccount use case."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from admin.application.api_keys.use_cases import CreateAccount
from admin.domain.api_keys.entities.account import Account


class TestCreateAccount:
    """Tests for CreateAccount use case."""

    @pytest.fixture
    def mock_account_repo(self) -> AsyncMock:
        """Create a mock AccountRepository."""
        return AsyncMock()

    @pytest.fixture
    def use_case(self, mock_account_repo: AsyncMock) -> CreateAccount:
        """Create a CreateAccount use case with mock dependencies."""
        return CreateAccount(account_repo=mock_account_repo)

    @pytest.mark.asyncio
    async def test_creates_account_with_given_id(
        self,
        use_case: CreateAccount,
        mock_account_repo: AsyncMock,
    ) -> None:
        """CreateAccount should create an account with the given ID."""
        account_id = uuid4()

        result = await use_case.execute(account_id)

        assert result.id == account_id
        assert isinstance(result.created_at, datetime)

    @pytest.mark.asyncio
    async def test_saves_account_to_repository(
        self,
        use_case: CreateAccount,
        mock_account_repo: AsyncMock,
    ) -> None:
        """CreateAccount should save the account to the repository."""
        account_id = uuid4()

        await use_case.execute(account_id)

        mock_account_repo.save.assert_called_once()
        saved_account = mock_account_repo.save.call_args[0][0]
        assert isinstance(saved_account, Account)
        assert saved_account.id == account_id

    @pytest.mark.asyncio
    async def test_returns_account_entity(
        self,
        use_case: CreateAccount,
        mock_account_repo: AsyncMock,
    ) -> None:
        """CreateAccount should return an Account entity."""
        account_id = uuid4()

        result = await use_case.execute(account_id)

        assert isinstance(result, Account)

    @pytest.mark.asyncio
    async def test_created_at_is_utc(
        self,
        use_case: CreateAccount,
        mock_account_repo: AsyncMock,
    ) -> None:
        """CreateAccount should set created_at to UTC time."""
        account_id = uuid4()
        before = datetime.now(UTC)

        result = await use_case.execute(account_id)

        after = datetime.now(UTC)
        assert before <= result.created_at <= after
