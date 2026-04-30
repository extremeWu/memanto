"""
Health Check Routes
"""

from fastapi import APIRouter, Depends
from moorcheh_sdk import MoorchehClient

from memanto.app import __version__
from memanto.app.clients.moorcheh import get_moorcheh_client
from memanto.app.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(client: MoorchehClient = Depends(get_moorcheh_client)):
    """Health check endpoint"""

    # Test Moorcheh connection
    moorcheh_connected = False
    try:
        from moorcheh_sdk.exceptions import AuthenticationError, NamespaceNotFound

        try:
            # Dummy fetch to test connection
            client.documents.get(namespace_name="__memanto_auth_ping__", ids=["1"])
            moorcheh_connected = True
        except NamespaceNotFound:
            moorcheh_connected = True
        except AuthenticationError:
            moorcheh_connected = False
    except Exception:
        moorcheh_connected = False

    return HealthResponse(
        status="healthy" if moorcheh_connected else "degraded",
        service="MEMANTO",
        version=__version__,
        moorcheh_connected=moorcheh_connected,
    )


@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {"status": "alive"}
