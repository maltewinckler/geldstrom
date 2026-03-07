"""BankingClient port — protocol-agnostic banking operations.

Note: BankingClient returns FetchResult and accepts PendingChallenge, both of
which are session-domain types. To avoid a cross-domain circular import
(session → banking → session), BankingClient is re-exported from
gateway.domain.ports which sits above both sub-domains.

This file is intentionally empty — see gateway.domain.ports.
"""
