from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
from src.config import get_settings
from src.database import get_db

router = APIRouter(prefix="/health", tags=["Health"])
@router.get("/", summary="Health Check")
def health_check(db: Session = Depends(get_db)):
    settings = get_settings()
    # Perform a simple database query to check connectivity
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
