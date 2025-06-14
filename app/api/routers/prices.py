from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import Optional, List
from sqlalchemy.orm import Session

from app.schemas.prices import (
    PriceResponse, PollRequest, PollResponse, ErrorResponse, MovingAverageResponse
)
from app.services.market_data import MarketDataService
from app.core.database import get_db
from app.api.dependencies import (
    get_market_data_service, validate_symbol, validate_provider
)

router = APIRouter(prefix="/prices", tags=["Prices"])


@router.get(
    "/latest",
    response_model=PriceResponse,
    summary="Get Latest Price",
    description="Fetch the most recent price for a stock symbol with intelligent caching",
    responses={
        200: {
            "description": "Latest price retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "symbol": "AAPL",
                        "price": 196.45,
                        "timestamp": "2025-06-14T18:05:48.660453",
                        "provider": "alpha_vantage"
                    }
                }
            }
        },
        400: {"model": ErrorResponse, "description": "Invalid symbol or provider"},
        404: {"model": ErrorResponse, "description": "Symbol not found"},
        503: {"model": ErrorResponse, "description": "Service temporarily unavailable"}
    }
)
async def get_latest_price(
    symbol: str = Query(
        ..., 
        description="Stock symbol (e.g., AAPL, MSFT, GOOGL)", 
        example="AAPL",
        min_length=1,
        max_length=10,
        regex="^[A-Za-z]{1,10}$"
    ),
    provider: Optional[str] = Query(
        None, 
        description="Market data provider", 
        example="alpha_vantage",
        enum=["alpha_vantage", "yahoo", "finnhub"]
    ),
    use_cache: bool = Query(
        True, 
        description="Use cached data if available (5-minute TTL)"
    ),
    service: MarketDataService = Depends(get_market_data_service),
    db: Session = Depends(get_db)
):
    """
    Get Latest Stock Price
    Retrieves the most recent price for a specified stock symbol with intelligent caching and database persistence.
    
    """
    try:
        symbol = validate_symbol(symbol)
        provider = validate_provider(provider)
        
        price_data = await service.get_latest_price(
            symbol=symbol, 
            provider=provider, 
            db=db, 
            use_cache=use_cache
        )
        
        return PriceResponse(
            symbol=price_data["symbol"],
            price=price_data["price"],
            timestamp=price_data["timestamp"],
            provider=price_data["provider"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service temporarily unavailable: {str(e)}"
        )


@router.get(
    "/history/{symbol}",
    response_model=List[PriceResponse],
    summary="Get Price History",
    description="Retrieve historical price data for a stock symbol",
    responses={
        200: {
            "description": "Price history retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "symbol": "AAPL",
                            "price": 196.45,
                            "timestamp": "2025-06-14T18:05:48.660453",
                            "provider": "alpha_vantage"
                        },
                        {
                            "symbol": "AAPL",
                            "price": 195.80,
                            "timestamp": "2025-06-14T17:30:22.123456",
                            "provider": "alpha_vantage"
                        }
                    ]
                }
            }
        },
        400: {"model": ErrorResponse, "description": "Invalid symbol or parameters"},
        404: {"model": ErrorResponse, "description": "No historical data found"}
    }
)
async def get_price_history(
    symbol: str = Path(
        ..., 
        description="Stock symbol", 
        example="AAPL",
        min_length=1,
        max_length=10,
        regex="^[A-Za-z]{1,10}$"
    ),
    hours: int = Query(
        24, 
        ge=1, 
        le=168, 
        description="Hours of history to retrieve (1-168 hours = 1-7 days)",
        example=24
    ),
    service: MarketDataService = Depends(get_market_data_service),
    db: Session = Depends(get_db)
):
    """
    Get Price History
    Retrieves historical price data for a stock symbol from the database.
    
    """
    try:
        symbol = validate_symbol(symbol)
        
        history = service.get_price_history(symbol=symbol, hours=hours, db=db)
        
        return [
            PriceResponse(
                symbol=h["symbol"],
                price=h["price"],
                timestamp=h["timestamp"],
                provider=h["provider"]
            )
            for h in history
        ]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/moving-average/{symbol}",
    response_model=MovingAverageResponse,
    summary="Get Moving Average",
    description="Get the latest calculated moving average for a stock symbol",
    tags=["Moving Averages"],
    responses={
        200: {
            "description": "Moving average retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "symbol": "AAPL",
                        "moving_average": 195.82,
                        "period": 5,
                        "timestamp": "2025-06-14T18:05:48.660453"
                    }
                }
            }
        },
        400: {"model": ErrorResponse, "description": "Invalid symbol or period"},
        404: {"model": ErrorResponse, "description": "No moving average data found"}
    }
)
async def get_moving_average(
    symbol: str = Path(
        ..., 
        description="Stock symbol", 
        example="AAPL",
        min_length=1,
        max_length=10,
        regex="^[A-Za-z]{1,10}$"
    ),
    period: int = Query(
        5, 
        ge=2, 
        le=50, 
        description="Moving average period (number of data points)",
        example=5
    ),
    service: MarketDataService = Depends(get_market_data_service),
    db: Session = Depends(get_db)
):
    """
    Get Moving Average
    Retrieves the latest calculated moving average for a stock symbol from the Kafka streaming pipeline.
      
    """
    try:
        symbol = validate_symbol(symbol)
        
        ma_data = service.get_moving_average(symbol=symbol, period=period, db=db)
        
        if not ma_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No moving average data found for {symbol} with {period}-point period. Ensure you have at least {period} price data points."
            )
        
        return MovingAverageResponse(
            symbol=ma_data["symbol"],
            moving_average=ma_data["moving_average"],
            period=ma_data["period"],
            timestamp=ma_data["timestamp"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/poll",
    response_model=PollResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start Polling Job",
    description="Create a background job to continuously poll multiple symbols",
    tags=["Polling Jobs"],
    responses={
        202: {
            "description": "Polling job created successfully",
            "content": {
                "application/json": {
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
            }
        },
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        503: {"model": ErrorResponse, "description": "Service temporarily unavailable"}
    }
)
async def start_polling(
    request: PollRequest,
    service: MarketDataService = Depends(get_market_data_service),
    db: Session = Depends(get_db)
):
    """
    Start Polling Job
    Creates a background job that continuously fetches price data for multiple symbols at specified intervals.
    
    """
    try:
        validated_symbols = [validate_symbol(s) for s in request.symbols]
        
        job_id = await service.start_polling_job(
            symbols=validated_symbols,
            interval=request.interval,
            provider=request.provider,
            db=db
        )
        
        return PollResponse(
            job_id=job_id,
            status="accepted",
            config={
                "symbols": validated_symbols,
                "interval": request.interval,
                "provider": request.provider or "alpha_vantage"
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to start polling job: {str(e)}"
        )


@router.get(
    "/poll/{job_id}",
    summary="Get Polling Job Status",
    description="Retrieve the current status and configuration of a polling job",
    tags=["Polling Jobs"],
    responses={
        200: {
            "description": "Polling job status retrieved successfully",
            "content": {
                "application/json": {
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
                        "next_run": "2025-06-14T18:06:00.000000"
                    }
                }
            }
        },
        404: {"model": ErrorResponse, "description": "Polling job not found"}
    }
)
async def get_polling_job_status(
    job_id: str = Path(..., description="Polling job identifier", example="poll_a1b2c3d4"),
    service: MarketDataService = Depends(get_market_data_service),
    db: Session = Depends(get_db)
):
    """
    Get Polling Job Status
    Retrieves detailed status information for a specific polling job.
    
    """
    job = service.get_polling_job(job_id, db=db)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Polling job {job_id} not found"
        )
    
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "config": {
            "symbols": job["symbols"],
            "interval": job["interval"],
            "provider": job["provider"]
        },
        "created_at": job["created_at"],
        "last_run": job["last_run"],
        "next_run": job["next_run"] if job["status"] == "active" else None,
        "error_message": job.get("error_message")
    }


@router.delete(
    "/poll/{job_id}",
    summary="Stop Polling Job",
    description="Stop a running polling job",
    tags=["Polling Jobs"],
    responses={
        200: {
            "description": "Polling job stopped successfully",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "poll_a1b2c3d4",
                        "status": "stopped",
                        "message": "Polling job stopped successfully"
                    }
                }
            }
        },
        404: {"model": ErrorResponse, "description": "Polling job not found"}
    }
)
async def stop_polling_job(
    job_id: str = Path(..., description="Polling job identifier to stop", example="poll_a1b2c3d4"),
    service: MarketDataService = Depends(get_market_data_service),
    db: Session = Depends(get_db)
):
    """
    Stop Polling Job
    Stops a running polling job and updates its status in the database.
    
    """
    success = service.stop_polling_job(job_id, db=db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Polling job {job_id} not found"
        )
    
    return {
        "job_id": job_id,
        "status": "stopped",
        "message": "Polling job stopped successfully"
    }