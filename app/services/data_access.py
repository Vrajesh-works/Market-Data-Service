from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from app.models.database import (
    RawMarketData, ProcessedPricePoint, MovingAverage, PollingJobConfig
)


class DataAccessLayer:
    
    def __init__(self, db: Session):
        self.db = db
    
    # Raw Market Data operations
    def save_raw_market_data(self, symbol: str, provider: str, raw_response: Dict[str, Any]) -> RawMarketData:
        raw_data = RawMarketData(
            symbol=symbol.upper(),
            provider=provider,
            raw_response=raw_response
        )
        self.db.add(raw_data)
        self.db.commit()
        self.db.refresh(raw_data)
        return raw_data
    
    def get_raw_market_data(self, symbol: str = None, provider: str = None, 
                           limit: int = 100) -> List[RawMarketData]:
        query = self.db.query(RawMarketData)
        
        if symbol:
            query = query.filter(RawMarketData.symbol == symbol.upper())
        if provider:
            query = query.filter(RawMarketData.provider == provider)
        
        return query.order_by(desc(RawMarketData.timestamp)).limit(limit).all()
    
    # Processed Price Points operations
    def save_price_point(self, symbol: str, price: float, timestamp: datetime, 
                        provider: str, raw_response_id: UUID) -> ProcessedPricePoint:
        price_point = ProcessedPricePoint(
            symbol=symbol.upper(),
            price=price,
            timestamp=timestamp,
            provider=provider,
            raw_response_id=raw_response_id
        )
        self.db.add(price_point)
        self.db.commit()
        self.db.refresh(price_point)
        return price_point
    
    def get_latest_price(self, symbol: str, provider: str = None) -> Optional[ProcessedPricePoint]:
        query = self.db.query(ProcessedPricePoint).filter(
            ProcessedPricePoint.symbol == symbol.upper()
        )
        
        if provider:
            query = query.filter(ProcessedPricePoint.provider == provider)
        
        return query.order_by(desc(ProcessedPricePoint.timestamp)).first()
    
    def get_price_history(self, symbol: str, hours: int = 24, provider: str = None) -> List[ProcessedPricePoint]:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        query = self.db.query(ProcessedPricePoint).filter(
            and_(
                ProcessedPricePoint.symbol == symbol.upper(),
                ProcessedPricePoint.timestamp >= since
            )
        )
        
        if provider:
            query = query.filter(ProcessedPricePoint.provider == provider)
        
        return query.order_by(desc(ProcessedPricePoint.timestamp)).all()
    
    def get_last_n_prices(self, symbol: str, n: int = 5, provider: str = None) -> List[ProcessedPricePoint]:
        query = self.db.query(ProcessedPricePoint).filter(
            ProcessedPricePoint.symbol == symbol.upper()
        )
        
        if provider:
            query = query.filter(ProcessedPricePoint.provider == provider)
        
        return query.order_by(desc(ProcessedPricePoint.timestamp)).limit(n).all()
    
    # Moving Average operations
    def save_moving_average(self, symbol: str, moving_average: float, 
                           period: int = 5) -> MovingAverage:
        ma = MovingAverage(
            symbol=symbol.upper(),
            moving_average=moving_average,
            period=period,
            timestamp=datetime.utcnow()
        )
        self.db.add(ma)
        self.db.commit()
        self.db.refresh(ma)
        return ma
    
    def get_latest_moving_average(self, symbol: str, period: int = 5) -> Optional[MovingAverage]:
        return self.db.query(MovingAverage).filter(
            and_(
                MovingAverage.symbol == symbol.upper(),
                MovingAverage.period == period
            )
        ).order_by(desc(MovingAverage.timestamp)).first()
    
    def get_moving_average_history(self, symbol: str, period: int = 5, 
                                  hours: int = 24) -> List[MovingAverage]:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        return self.db.query(MovingAverage).filter(
            and_(
                MovingAverage.symbol == symbol.upper(),
                MovingAverage.period == period,
                MovingAverage.timestamp >= since
            )
        ).order_by(desc(MovingAverage.timestamp)).all()
    
    # Polling Job operations
    def save_polling_job(self, job_id: str, symbols: List[str], interval: int, 
                        provider: str) -> PollingJobConfig:
        job = PollingJobConfig(
            job_id=job_id,
            symbols=symbols,
            interval=interval,
            provider=provider,
            status='active',
            next_run=datetime.utcnow()
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
    
    def get_polling_job(self, job_id: str) -> Optional[PollingJobConfig]:
        return self.db.query(PollingJobConfig).filter(
            PollingJobConfig.job_id == job_id
        ).first()
    
    def update_polling_job_status(self, job_id: str, status: str, 
                                 error_message: str = None) -> bool:
        job = self.get_polling_job(job_id)
        if job:
            job.status = status
            job.updated_at = datetime.utcnow()
            if error_message:
                job.error_message = error_message
            self.db.commit()
            return True
        return False
    
    def update_polling_job_run_time(self, job_id: str, last_run: datetime, 
                                   next_run: datetime) -> bool:
        job = self.get_polling_job(job_id)
        if job:
            job.last_run = last_run
            job.next_run = next_run
            job.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False
    
    def get_active_polling_jobs(self) -> List[PollingJobConfig]:
        return self.db.query(PollingJobConfig).filter(
            PollingJobConfig.status == 'active'
        ).all()
    
    def get_jobs_due_for_execution(self) -> List[PollingJobConfig]:
        now = datetime.utcnow()
        return self.db.query(PollingJobConfig).filter(
            and_(
                PollingJobConfig.status == 'active',
                PollingJobConfig.next_run <= now
            )
        ).all()