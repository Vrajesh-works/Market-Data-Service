import os
from typing import Optional

class AWSConfig:
    # Database
    DATABASE_URL = os.getenv("postgresql://postgres:NewPassword123@database-1.cxwgqug0ag3v.us-east-2.rds.amazonaws.com:5432/postgres")
    
    # Market data provider
    ALPHA_VANTAGE_API_KEY = os.getenv("JY9I4H2B0LQ8Y40W")
    
    # Simplified queue (using database instead of Kafka)
    KAFKA_DISABLED = os.getenv("KAFKA_DISABLED", "false").lower() == "true"
    
    # AWS specific
    AWS_REGION = os.getenv("AWS_REGION", "us-east-2")