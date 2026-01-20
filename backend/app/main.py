from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from .config import settings
from .database import connect_to_mongo, close_mongo_connection, ping_database
from .routers import auth, items, tags, chat
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(
    title="ContentStash API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
cors_origins = settings.cors_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log detailed validation errors for debugging"""
    logger.error(f"=== VALIDATION ERROR ===")
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Request method: {request.method}")
    logger.error(f"Validation errors: {exc.errors()}")
    logger.error(f"Request body: {await request.body()}")
    logger.error(f"========================")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

# Register routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(items.router, prefix="/api/v1/items", tags=["items"])
app.include_router(tags.router, prefix="/api/v1/tags", tags=["tags"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])


@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    db_connected = await ping_database()
    return {
        "status": "ok",
        "database": "connected" if db_connected else "disconnected"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "ContentStash API", "version": "1.0.0"}