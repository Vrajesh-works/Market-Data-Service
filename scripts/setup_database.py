
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force reload environment variables
from dotenv import load_dotenv
load_dotenv(override=True)

from app.core.database import db_manager
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_database(max_attempts=30, delay=2):
    logger.info("Waiting for database to be ready...")
    
    for attempt in range(max_attempts):
        try:
            if db_manager.health_check():
                logger.info("Database is ready!")
                return True
            else:
                logger.info(f"Attempt {attempt + 1}/{max_attempts}: Database not ready, waiting {delay}s...")
                time.sleep(delay)
        except Exception as e:
            logger.info(f"Attempt {attempt + 1}/{max_attempts}: Connection failed ({e}), waiting {delay}s...")
            time.sleep(delay)
    
    return False


def main():
    logger.info("Setting up Market Data Service database...")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    
    # Wait for database to be ready
    if not wait_for_database():
        logger.error("Database is not ready after waiting. Please check your Docker containers.")
        logger.error("Try: docker-compose logs postgres")
        sys.exit(1)
    
    try:
        logger.info("Creating database tables...")
        db_manager.create_tables()
        logger.info("Database tables created successfully")
        
        from sqlalchemy import inspect
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'raw_market_data',
            'processed_price_points', 
            'moving_averages',
            'polling_job_configs'
        ]
        
        logger.info(f"Found tables: {tables}")
        
        for table in expected_tables:
            if table in tables:
                logger.info(f"✓ Table '{table}' created successfully")
            else:
                logger.error(f"✗ Table '{table}' was not created")
        
        logger.info("Database setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()