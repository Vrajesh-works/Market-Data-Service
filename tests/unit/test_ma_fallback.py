"""Moving-average fallback: computed from price history when the
Kafka consumer has not populated the moving_averages table."""
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.services.data_access import DataAccessLayer
from app.services.market_data import MarketDataService


def _seed_prices(db, symbol="AAPL", n=5):
    dal = DataAccessLayer(db)
    base = datetime(2026, 10, 6, 12, 0, 0)
    for i in range(n):
        raw = dal.save_raw_market_data(
            symbol=symbol, provider="stooq", raw_response={"i": i}
        )
        dal.save_price_point(
            symbol=symbol,
            price=100.0 + i,
            timestamp=base + timedelta(minutes=i),
            provider="stooq",
            raw_response_id=raw.id,
        )


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_ma_fallback_computes_from_history():
    db = _session()
    _seed_prices(db, n=5)
    service = MarketDataService.__new__(MarketDataService)
    result = service.get_moving_average("AAPL", period=5, db=db)
    assert result is not None
    assert result["moving_average"] == (100 + 101 + 102 + 103 + 104) / 5
    assert result["period"] == 5
    db.close()


def test_ma_fallback_returns_none_without_enough_points():
    db = _session()
    _seed_prices(db, n=3)
    service = MarketDataService.__new__(MarketDataService)
    assert service.get_moving_average("AAPL", period=5, db=db) is None
    db.close()


def test_ma_prefers_kafka_computed_value():
    db = _session()
    _seed_prices(db, n=5)
    dal = DataAccessLayer(db)
    dal.save_moving_average(symbol="AAPL", moving_average=999.0, period=5)
    service = MarketDataService.__new__(MarketDataService)
    result = service.get_moving_average("AAPL", period=5, db=db)
    assert result["moving_average"] == 999.0
    db.close()
