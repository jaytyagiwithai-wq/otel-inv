from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from opentelemetry.trace import Tracer
from sqlalchemy.orm import Session
from otel_b.infrastructure.db.session import get_db_session
from otel_b.core.config import get_settings

SessionDep = Annotated[
    Session,
    Depends(get_db_session, scope="function")
]


def get_lab_tenant_id(tenant_id: Annotated[UUID, Header(alias="X-Tenant-ID")]) -> UUID:
    if get_settings().environment not in {"local", "test"}:
        raise HTTPException(
            status_code=503,
            detail="Lab tenant identity is disabled",
        )
    return tenant_id




def get_application_tracer(request: Request) -> Tracer:
    provider = request.app.state.tracer_provider
    return provider.get_tracer("otel_b.orders")


TenantDep = Annotated[UUID, Depends(get_lab_tenant_id)]
TracerDep = Annotated[Tracer, Depends(get_application_tracer)]
