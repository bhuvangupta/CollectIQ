from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
    error_code: Optional[str] = None


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""
    total: int
    successful: int
    failed: int
    errors: List[dict] = []


class DateRangeFilter(BaseModel):
    """Date range filter."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class IDResponse(BaseModel):
    """Response with just an ID."""
    id: UUID


class CountResponse(BaseModel):
    """Response with a count."""
    count: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    app: str
    version: str = "1.0.0"
