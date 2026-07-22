from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {
        "success": True,
        "service": "UMA Geo Service",
        "status": "healthy"
    }
