from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.router import api_router

# Sensitive field names to redact from logs
SENSITIVE_FIELDS = {
    "password", "current_password", "new_password", "confirm_password",
    "token", "access_token", "refresh_token", "api_key", "secret",
    "authorization", "cookie", "credit_card", "ssn", "pan"
}

# Rate limiter - uses client IP address
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


def sanitize_error_data(errors: list) -> list:
    """Sanitize validation errors to remove sensitive field values."""
    sanitized = []
    for error in errors:
        error_copy = dict(error)
        # Check if error is for a sensitive field
        loc = error_copy.get("loc", [])
        field_name = loc[-1] if loc else ""
        if isinstance(field_name, str) and field_name.lower() in SENSITIVE_FIELDS:
            # Redact the input value if present
            if "input" in error_copy:
                error_copy["input"] = "[REDACTED]"
        sanitized.append(error_copy)
    return sanitized


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting application", app_name=settings.app_name)
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down application")


app = FastAPI(
    title=settings.app_name,
    description="AI-Powered Loan Collection Platform API",
    version="1.0.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
    lifespan=lifespan,
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - origins configurable via CORS_ORIGINS env var
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    """Handle validation errors."""
    # Sanitize errors to remove sensitive field values from logs
    sanitized_errors = sanitize_error_data(exc.errors())
    logger.warning(
        "Validation error",
        path=request.url.path,
        errors=sanitized_errors
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors()  # Return full errors to client for debugging
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": f"{settings.api_v1_prefix}/docs"
    }
