from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

Base = declarative_base()


class RawMarketData(Base):
    __tablename__ = "raw_market_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(10), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    raw_response = Column(JSONB, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    price_points = relationship("ProcessedPricePoint", back_populates="raw_data")
    
    __table_args__ = (
        Index('idx_raw_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_raw_provider_timestamp', 'provider', 'timestamp'),
    )


class ProcessedPricePoint(Base):
    __tablename__ = "processed_price_points"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(10), nullable=False, index=True)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    raw_response_id = Column(UUID(as_uuid=True), ForeignKey('raw_market_data.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    
    raw_data = relationship("RawMarketData", back_populates="price_points")
    
    __table_args__ = (
        Index('idx_price_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_price_symbol_provider', 'symbol', 'provider'),
    )


class MovingAverage(Base):
    __tablename__ = "moving_averages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(10), nullable=False, index=True)
    moving_average = Column(Float, nullable=False)
    period = Column(Integer, nullable=False, default=5)
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
 
    __table_args__ = (
        Index('idx_ma_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_ma_symbol_period', 'symbol', 'period'),
    )


class PollingJobConfig(Base):
    __tablename__ = "polling_job_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String(50), unique=True, nullable=False, index=True)
    symbols = Column(JSONB, nullable=False)
    interval = Column(Integer, nullable=False)
    provider = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default='active')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_job_status_next_run', 'status', 'next_run'),
    )