from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ProviderEnum(str, Enum):
    ALPHA_VANTAGE = "alpha_vantage"
    YAHOO = "yahoo"
    FINNHUB = "finnhub"


class PriceResponse(BaseModel):
    
    symbol: str = Field(
        ..., 
        description="Stock symbol", 
        example="AAPL",
        min_length=1,
        max_length=10
    )
    price: float = Field(
        ..., 
        description="Current stock price in USD", 
        example=196.45,
        gt=0
    )
    timestamp: datetime = Field(
        ..., 
        description="When the price was fetched (ISO 8601 format)",
        example="2025-06-14T18:05:48.660453"
    )
    provider: str = Field(
        ..., 
        description="Market data provider name", 
        example="alpha_vantage"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "price": 196.45,
                "timestamp": "2025-06-14T18:05:48.660453",
                "provider": "alpha_vantage"
            }
        }


class PollRequest(BaseModel):
    
    symbols: List[str] = Field(
        ..., 
        description="List of stock symbols to poll",
        example=["AAPL", "MSFT", "GOOGL"],
        min_items=1, 
        max_items=10
    )
    interval: int = Field(
        60, 
        description="Polling interval in seconds",
        example=60,
        ge=30, 
        le=3600
    )
    provider: Optional[ProviderEnum] = Field(
        None,
        description="Market data provider (defaults to alpha_vantage)",
        example="alpha_vantage"
    )
    
    @validator('symbols')
    def validate_symbols(cls, v):
        for symbol in v:
            if not symbol or len(symbol) > 10 or not symbol.isalpha():
                raise ValueError(f"Invalid symbol format: {symbol}")
        return [s.upper() for s in v]
    
    class Config:
        schema_extra = {
            "example": {
                "symbols": ["AAPL", "MSFT", "GOOGL"],
                "interval": 60,
                "provider": "alpha_vantage"
            }
        }


class PollResponse(BaseModel):
    
    job_id: str = Field(
        ..., 
        description="Unique job identifier",
        example="poll_a1b2c3d4"
    )
    status: str = Field(
        "accepted", 
        description="Job status",
        example="accepted"
    )
    config: dict = Field(
        ..., 
        description="Job configuration details",
        example={
            "symbols": ["AAPL", "MSFT"],
            "interval": 60,
            "provider": "alpha_vantage"
        }
    )
    
    class Config:
        schema_extra = {
            "example": {
                "job_id": "poll_a1b2c3d4",
                "status": "accepted",
                "config": {
                    "symbols": ["AAPL", "MSFT"],
                    "interval": 60,
                    "provider": "alpha_vantage"
                }
            }
        }


class MovingAverageResponse(BaseModel):    
    symbol: str = Field(
        ..., 
        description="Stock symbol",
        example="AAPL"
    )
    moving_average: float = Field(
        ..., 
        description="Calculated moving average price",
        example=195.82
    )
    period: int = Field(
        5, 
        description="Number of data points used in calculation",
        example=5
    )
    timestamp: datetime = Field(
        ..., 
        description="When the moving average was calculated",
        example="2025-06-14T18:05:48.660453"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "moving_average": 195.82,
                "period": 5,
                "timestamp": "2025-06-14T18:05:48.660453"
            }
        }


class ErrorResponse(BaseModel):    
    error: str = Field(
        ..., 
        description="Error message describing what went wrong",
        example="Symbol 'INVALID' not found"
    )
    detail: Optional[str] = Field(
        None, 
        description="Additional error details",
        example="The requested symbol is not supported by the provider"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the error occurred",
        example="2025-06-14T18:05:48.660453"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "error": "Symbol 'INVALID' not found",
                "detail": "The requested symbol is not supported by the provider",
                "timestamp": "2025-06-14T18:05:48.660453"
            }
        }


class JobStatusResponse(BaseModel):    
    job_id: str = Field(
        ..., 
        description="Unique job identifier",
        example="poll_a1b2c3d4"
    )
    status: str = Field(
        ..., 
        description="Current job status",
        example="active"
    )
    config: dict = Field(
        ..., 
        description="Job configuration",
        example={
            "symbols": ["AAPL", "MSFT"],
            "interval": 60,
            "provider": "alpha_vantage"
        }
    )
    created_at: datetime = Field(
        ..., 
        description="When the job was created",
        example="2025-06-14T18:00:00.000000"
    )
    last_run: Optional[datetime] = Field(
        None, 
        description="Last execution time",
        example="2025-06-14T18:05:00.000000"
    )
    next_run: Optional[datetime] = Field(
        None, 
        description="Next scheduled execution",
        example="2025-06-14T18:06:00.000000"
    )
    error_message: Optional[str] = Field(
        None, 
        description="Error message if job failed",
        example=None
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "job_id": "poll_a1b2c3d4",
                "status": "active",
                "config": {
                    "symbols": ["AAPL", "MSFT"],
                    "interval": 60,
                    "provider": "alpha_vantage"
                },
                "created_at": "2025-06-14T18:00:00.000000",
                "last_run": "2025-06-14T18:05:00.000000",
                "next_run": "2025-06-14T18:06:00.000000",
                "error_message": None
            }
        }


class HealthResponse(BaseModel):    
    status: str = Field(
        ..., 
        description="Overall system health status",
        example="healthy"
    )
    service: str = Field(
        ..., 
        description="Service name",
        example="Market Data Service"
    )
    version: str = Field(
        ..., 
        description="Service version",
        example="1.0.0"
    )
    database: str = Field(
        ..., 
        description="Database connection status",
        example="connected"
    )
    components: dict = Field(
        ..., 
        description="Individual component health status",
        example={
            "api": "healthy",
            "database": "healthy",
            "providers": ["alpha_vantage"]
        }
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "service": "Market Data Service",
                "version": "1.0.0",
                "database": "connected",
                "components": {
                    "api": "healthy",
                    "database": "healthy",
                    "providers": ["alpha_vantage"]
                }
            }
        }