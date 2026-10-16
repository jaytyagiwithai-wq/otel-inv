from fastapi import HTTPException, APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from opentelemetry import trace
from otel_b.api.dependencies import SessionDep
from otel_b.core.logging import log_event
from otel_b.modules.orders.router import router as orders_router

#The  Automatic instrumentation knows HTTPS, SQL details. Code must supply what operation means

router = APIRouter(prefix="/api/v1")
router.include_router(orders_router)

@router.get('/health', tags=["health"])
def health() -> dict[str,str]:
    return{"status":"ok"}


@router.get("/health/ready", tags=["health"])
def readiness(session: SessionDep) -> dict[str, str]:
    span = trace.get_current_span()
    span.set_attribute("app.operation","readiness.check")
    span.set_attribute("app.dependency","postgresql")
    try:
        with session.begin():

            session.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        span.set_attribute("app.outcome", "dependency_error")
        span.set_attribute("app.error.type", type(error).__name__)
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from error

    span.set_attribute("app.outcome","success")
    log_event(
    "readiness.check.completed",
    attributes={
        "app.operation": "readiness.check",
        "app.dependency": "postgresql",
        "app.outcome": "success",
    },
)

    return {"status": "ready"}
