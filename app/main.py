from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.users import router as users_router
from app.database import get_db

# This object represents our FastAPI application.
# Uvicorn imports this variable when we run `uvicorn app.main:app`.
app = FastAPI(
    title= "BananaKart API",
    description="The world's most chaotic banana marketplace"
    )

# Register the users router with the main FastAPI application.
#
# The router itself has prefix="/users", so this activates endpoints such as:
#
# POST /users
app.include_router(users_router)

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