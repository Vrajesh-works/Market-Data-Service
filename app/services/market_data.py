import uuid
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.providers.base import MarketDataProvider
from app.services.providers.alpha_vantage import AlphaVantageProvider
from app.services.data_access import DataAccessLayer
from app.services.kafka_producer import kafka_producer
from app.core.config import settings
from app.schemas.prices import ProviderEnum


class MarketDataService:
    # Service for managing market data operations with database persistence and Kafka integration
    
    def __init__(self):
        self.providers: Dict[str, MarketDataProvider] = {}
        self.polling_jobs: Dict[str, Dict[str, Any]] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        try:
            self.providers["alpha_vantage"] = AlphaVantageProvider()
        except ValueError as e:
            print(f"Warning: Could not initialize Alpha Vantage provider: {e}")
    
    def get_provider(self, provider_name: Optional[str] = None) -> MarketDataProvider:
        provider_name = provider_name or settings.DEFAULT_PROVIDER
        
        if provider_name not in self.providers:
            available = list(self.providers.keys())
            raise ValueError(f"Provider '{provider_name}' not available. Available: {available}")
        
        return self.providers[provider_name]
    
    async def get_latest_price(self, symbol: str, provider: Optional[str] = None, 
                              db: Session = None, use_cache: bool = True) -> Dict[str, Any]:
    
        #Get the latest price for a symbol with database persistence and Kafka publishing
        
        provider_instance = self.get_provider(provider)
        symbol = symbol.upper()
        
        if use_cache and db:
            dal = DataAccessLayer(db)
            recent_price = dal.get_latest_price(symbol, provider_instance.name)
            
            if recent_price and recent_price.timestamp > datetime.utcnow() - timedelta(minutes=5):
                return {
                    "symbol": recent_price.symbol,
                    "price": recent_price.price,
                    "timestamp": recent_price.timestamp,
                    "provider": recent_price.provider,
                    "source": "cache"
                }
        
        try:
            # Fetch fresh data from provider
            result = await provider_instance.get_latest_price(symbol)
            
            if db:
                dal = DataAccessLayer(db)
                
                raw_data = dal.save_raw_market_data(
                    symbol=symbol,
                    provider=provider_instance.name,
                    raw_response=result["raw_response"]
                )
                
                price_point = dal.save_price_point(
                    symbol=symbol,
                    price=result["price"],
                    timestamp=result["timestamp"],
                    provider=provider_instance.name,
                    raw_response_id=raw_data.id
                )
                
                kafka_producer.publish_price_event(
                    symbol=symbol,
                    price=result["price"],
                    timestamp=result["timestamp"],
                    provider=provider_instance.name,
                    raw_response_id=str(raw_data.id)
                )
                
            
            result["source"] = "live"
            return result
            
        except Exception as e:
            raise ValueError(f"Failed to get price for {symbol}: {str(e)}")
    
    async def start_polling_job(self, symbols: List[str], interval: int, 
                               provider: Optional[str] = None, db: Session = None) -> str:
        job_id = f"poll_{uuid.uuid4().hex[:8]}"
        
        if db:
            dal = DataAccessLayer(db)
            dal.save_polling_job(
                job_id=job_id,
                symbols=symbols,
                interval=interval,
                provider=provider or settings.DEFAULT_PROVIDER
            )
        
        job_config = {
            "job_id": job_id,
            "symbols": symbols,
            "interval": interval,
            "provider": provider or settings.DEFAULT_PROVIDER,
            "status": "active",
            "created_at": datetime.utcnow(),
            "last_run": None,
            "next_run": datetime.utcnow()
        }
        
        self.polling_jobs[job_id] = job_config
        
        asyncio.create_task(self._polling_worker(job_id, db))
        
        return job_id
    
    async def _polling_worker(self, job_id: str, db: Session = None):
        job = self.polling_jobs.get(job_id)
        if not job:
            return
        
        provider_instance = self.get_provider(job["provider"])
        
        while job["status"] == "active":
            try:
                if db:
                    dal = DataAccessLayer(db)
                    dal.update_polling_job_run_time(
                        job_id=job_id,
                        last_run=datetime.utcnow(),
                        next_run=datetime.utcnow() + timedelta(seconds=job["interval"])
                    )
                
                for symbol in job["symbols"]:
                    try:
                        price_data = await self.get_latest_price(
                            symbol=symbol,
                            provider=job["provider"],
                            db=db,
                            use_cache=False  
                        )
                        print(f"Polled {symbol}: ${price_data['price']} (Source: {price_data.get('source', 'unknown')}) → Kafka")
                        
                    except Exception as e:
                        print(f"Error polling {symbol}: {e}")
                        if db:
                            dal = DataAccessLayer(db)
                            dal.update_polling_job_status(job_id, "error", str(e))
                
                job["last_run"] = datetime.utcnow()
                job["next_run"] = datetime.utcnow() + timedelta(seconds=job["interval"])
                
                await asyncio.sleep(job["interval"])
                
            except Exception as e:
                print(f"Polling job {job_id} error: {e}")
                job["status"] = "error"
                
                if db:
                    dal = DataAccessLayer(db)
                    dal.update_polling_job_status(job_id, "error", str(e))
                break
    
    def get_polling_job(self, job_id: str, db: Session = None) -> Optional[Dict[str, Any]]:
        if db:
            dal = DataAccessLayer(db)
            job = dal.get_polling_job(job_id)
            if job:
                return {
                    "job_id": job.job_id,
                    "symbols": job.symbols,
                    "interval": job.interval,
                    "provider": job.provider,
                    "status": job.status,
                    "created_at": job.created_at,
                    "last_run": job.last_run,
                    "next_run": job.next_run,
                    "error_message": job.error_message
                }
        
        return self.polling_jobs.get(job_id)
    
    def stop_polling_job(self, job_id: str, db: Session = None) -> bool:
        if db:
            dal = DataAccessLayer(db)
            dal.update_polling_job_status(job_id, "stopped")
        
        if job_id in self.polling_jobs:
            self.polling_jobs[job_id]["status"] = "stopped"
            return True
        
        return db is not None 
    
    def get_price_history(self, symbol: str, hours: int = 24, 
                         db: Session = None) -> List[Dict[str, Any]]:
        if not db:
            return []
        
        dal = DataAccessLayer(db)
        history = dal.get_price_history(symbol, hours)
        
        return [
            {
                "symbol": p.symbol,
                "price": p.price,
                "timestamp": p.timestamp,
                "provider": p.provider
            }
            for p in history
        ]
    
    def get_moving_average(self, symbol: str, period: int = 5, 
                          db: Session = None) -> Optional[Dict[str, Any]]:
        if not db:
            return None
        
        dal = DataAccessLayer(db)
        ma = dal.get_latest_moving_average(symbol, period)
        
        if ma:
            return {
                "symbol": ma.symbol,
                "moving_average": ma.moving_average,
                "period": ma.period,
                "timestamp": ma.timestamp
            }
        
        return None


# Global service instance
market_data_service = MarketDataService()