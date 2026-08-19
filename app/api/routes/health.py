from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check probe",
    description="Public endpoint for load balancer, container, and orchestrator health probes. Exposes no sensitive data.",
)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="Jumbox", environment="development")
