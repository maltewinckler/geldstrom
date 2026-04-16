"""FastAPI dependency providers for the admin API."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory
from gateway_admin.application.factories.service_factory import ServiceFactory


def get_repo_factory(request: Request) -> AdminRepositoryFactory:
    return request.app.state.repo_factory


def get_service_factory(request: Request) -> ServiceFactory:
    return request.app.state.service_factory


RepoFactoryDep = Annotated[AdminRepositoryFactory, Depends(get_repo_factory)]
ServiceFactoryDep = Annotated[ServiceFactory, Depends(get_service_factory)]
