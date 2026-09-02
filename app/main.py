import logging
import time
import uuid
from fastapi.responses import JSONResponse
from fastapi import Depends, FastAPI, Request, HTTPException

from sqlalchemy import text
from app.database import SessionLocal
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes import auth, orders, users, products
from app.database import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

# This object represents our FastAPI application.
# Uvicorn imports this variable when we run `uvicorn app.main:app`.
app = FastAPI(
    title= "BananaKart API",
    description="The world's most chaotic banana marketplace"
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    try:
        response = await call_next(request)

    except Exception:
        duration_ms = (
            time.perf_counter() - start_time
        ) * 1000

        logger.exception(
            "request_id=%s | %s %s | status=500 | duration=%.2fms",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )

        raise

    duration_ms = (
        time.perf_counter() - start_time
    ) * 1000

    logger.info(
        "request_id=%s | %s %s | status=%s | duration=%.2fms",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    response.headers["X-Request-ID"] = request_id

    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error"
        },
    )

@app.get("/health/live", tags=["Health"])
def liveness():
    return {
        "status": "ok"
    }


@app.get("/health/ready", tags=["Health"])
def readiness():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))

        return {
            "status": "ready"
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )
# Register the users router with the main FastAPI application.
#
# The router itself has prefix="/users", so this activates endpoints such as:
#
# POST /users
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(products.router)

@app.get("/")
def home():
    """
    Basic route used to confirm that the FastAPI server is running.
    """
    return {
        "message" : "Welcome to BananaKart"
    }

@app.get("/health/database")
def database_health(db: Session = Depends(get_db)):
    # Depends tells FastAPI to call get_db() before running this endpoint.
    # The returned database session is passed into the `db` parameter.
    
    # SELECT 1 is a tiny query commonly used to test a database connection.
    # We are not reading any actual application data yet.
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }