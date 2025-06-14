from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Force reload environment variables
load_dotenv(override=True)

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Market Data Service"
    VERSION: str = "1.0.0"
    
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/marketdata"
    
    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 300  # 5 minutes
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_PRICE_EVENTS: str = "price-events"
    KAFKA_TOPIC_SYMBOL_AVERAGES: str = "symbol_averages"
    
    # Market Data Providers
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    DEFAULT_PROVIDER: str = "alpha_vantage"
    
    # Rate Limiting
    ALPHA_VANTAGE_RATE_LIMIT: int = 5 
    
    # Polling Configuration
    DEFAULT_POLL_INTERVAL: int = 60
    MAX_SYMBOLS_PER_POLL: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = 'utf-8'

settings = Settings()

# Debug: Print the DATABASE_URL to verify it's loaded correctly
print(f"DEBUG: Loaded DATABASE_URL = {settings.DATABASE_URL}")