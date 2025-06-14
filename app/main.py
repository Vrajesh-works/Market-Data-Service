from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import db_manager
from app.api.routes import prices

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Market Data Service...")
    
    try:
        db_manager.create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    if db_manager.health_check():
        logger.info("Database health check passed")
    else:
        logger.warning("Database health check failed - some features may not work")
    
    logger.info(f"Available providers: alpha_vantage")
    yield
    
    logger.info("Shutting down Market Data Service...")


# Create FastAPI application with enhanced OpenAPI documentation
app = FastAPI(
    title="Market Data Service API",
    version="1.0.0",
    description="""
    ## 🚀 Market Data Service API

    A production-ready microservice for fetching and processing real-time market data with streaming pipeline integration.

    ### 🎯 Key Features
    - *Real-time price data* from multiple providers
    - *Historical data* with configurable time ranges
    - *Moving averages* calculation via Kafka streaming
    - *Polling jobs* for continuous data collection
    - *Database persistence* with full audit trail
    - *Intelligent caching* with 5-minute TTL

    ### 📊 Data Providers
    - *Alpha Vantage*: Free tier with 5 calls/minute
    - *Yahoo Finance*: Coming soon
    - *Finnhub*: Coming soon

    ### 🔄 Data Pipeline
    1. API fetches data from provider
    2. Raw data stored in PostgreSQL
    3. Price events published to Kafka
    4. Consumers calculate moving averages
    5. Results stored and made available via API

    ### 🛡 Rate Limiting
    - Alpha Vantage: 5 calls per minute
    - Built-in caching reduces API calls
    - Polling jobs respect rate limits

    ### 📝 Usage Tips
    - Use use_cache=false to force fresh data
    - Moving averages require 5+ data points
    - Polling jobs run continuously until stopped
    - Check /health endpoint for system status
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Market Data Service Github",
        "url": "https://github.com/Vrajesh-works/Market-Data-Service"
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.marketdata.service",
            "description": "Production server"
        }
    ],
    tags_metadata=[
        {
            "name": "Health",
            "description": "System health and status endpoints"
        },
        {
            "name": "Prices",
            "description": "Real-time and historical price data operations"
        },
        {
            "name": "Moving Averages",
            "description": "Calculated moving averages from streaming pipeline"
        },
        {
            "name": "Polling Jobs",
            "description": "Background job management for continuous data collection"
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prices.router, prefix=settings.API_V1_STR)


@app.get(
    "/",
    tags=["Root"],
    summary="API Root",
    description="Welcome endpoint with basic API information and navigation links"
)
async def root():
    """
    API Root Endpoint
    
    Returns basic information about the Market Data Service API including:

    """
    return {
        "message": "Market Data Service API",
        "version": settings.VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "features": [
            "Real-time price data",
            "Price history",
            "Moving averages",
            "Polling jobs",
            "Database persistence",
            "Kafka streaming pipeline"
        ],
        "endpoints": {
            "health": "/health",
            "prices": "/api/v1/prices",
            "documentation": "/docs"
        }
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="System Health Check",
    description="Comprehensive health check for all system components",
    responses={
        200: {
            "description": "System is healthy",
            "content": {
                "application/json": {
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
            }
        },
        503: {
            "description": "System is degraded",
            "content": {
                "application/json": {
                    "example": {
                        "status": "degraded",
                        "service": "Market Data Service",
                        "version": "1.0.0",
                        "database": "disconnected",
                        "components": {
                            "api": "healthy",
                            "database": "unhealthy",
                            "providers": ["alpha_vantage"]
                        }
                    }
                }
            }
        }
    }
)
async def health_check():
    """
    System Health Check
    
    Performs a comprehensive health check of all system components:
    """
    database_healthy = db_manager.health_check()
    
    return {
        "status": "healthy" if database_healthy else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "connected" if database_healthy else "disconnected",
        "components": {
            "api": "healthy",
            "database": "healthy" if database_healthy else "unhealthy",
            "providers": ["alpha_vantage"]
        }
    }


@app.get(
    "/health/database",
    tags=["Health"],
    summary="Database Health Check",
    description="Specific health check for database connectivity and performance",
    responses={
        200: {
            "description": "Database is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "database": "connected",
                        "message": "Database is accessible"
                    }
                }
            }
        },
        503: {
            "description": "Database is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Database is not accessible",
                        "status_code": 503
                    }
                }
            }
        }
    }
)
async def database_health():
    """
    Database Health Check
    
    Performs a specific health check for the PostgreSQL database:
    """
    healthy = db_manager.health_check()
    
    if not healthy:
        raise HTTPException(status_code=503, detail="Database is not accessible")
    
    return {
        "status": "healthy",
        "database": "connected",
        "message": "Database is accessible"
    }


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500
        }
    )


if __name__ == "_main_":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )