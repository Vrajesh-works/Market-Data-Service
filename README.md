# Market Data Service

A production-ready microservice that fetches market data, processes it through a streaming pipeline, and serves it via REST APIs. Built with FastAPI, PostgreSQL, and Apache Kafka for real-time data processing.

## 🎯 Overview

This service provides:
- **Real-time market data** from multiple providers (Alpha Vantage, Yahoo Finance, Finnhub)
- **Database persistence** with PostgreSQL for historical data
- **Streaming data pipeline** using Apache Kafka for real-time processing
- **Moving averages calculation** via Kafka consumers
- **REST API endpoints** for data access and job management
- **Polling jobs** for continuous data collection

## 🏗️ Architecture

### System Architecture Diagram
```mermaid
graph TB
    subgraph "Market Data Service"
        API["FastAPI Service"]
        DB[(PostgreSQL)]
        Cache[("Redis Cache<br/>")]
    end
    
    subgraph "Message Queue"
        Kafka["Apache Kafka"]
        ZK["ZooKeeper"]
        Producer["Price Producer"]
        Consumer["MA Consumer"]
    end
    
    subgraph "External Services"
        MarketAPI["Market Data API<br/>(Alpha Vantage/YFinance)"]
    end
    
    subgraph "Monitoring"
        Prometheus["Prometheus<br/>[Optional]"]
        Grafana["Grafana<br/>[Optional]"]
    end
    
    Client["Client Application"] --> API
    API --> DB
    API --> Cache
    API --> MarketAPI
    
    API --> Producer
    Producer --> Kafka
    Kafka --> Consumer
    Consumer --> DB
    
    ZK <--> Kafka
    
    API --> Prometheus
    Prometheus --> Grafana
```

### Flow Diagram: illustrate data movement through the system
```mermaid
sequenceDiagram
    participant C as Client
    participant A as FastAPI
    participant M as Market API
    participant K as Kafka
    participant MA as MA Consumer
    participant DB as PostgreSQL
    
    C->>A: GET /prices/latest
    A->>DB: Check cache
    alt Cache miss
        A->>M: Fetch latest price
        M-->>A: Price data
        A->>DB: Store raw response
        A->>K: Produce price event
    end
    A-->>C: Return price
    
    K->>MA: Consume price event
    MA->>DB: Fetch last 5 prices
    MA->>MA: Calculate MA
    MA->>DB: Store MA resultV
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Alpha Vantage API Key (free from [alphavantage.co](https://www.alphavantage.co/support/#api-key))

### 1. Clone and Setup
```bash
git clone <repository-url>
cd market-data-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/base.txt
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration:
DATABASE_URL=postgresql://marketuser:marketpass123@localhost:5433/marketdata
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### 3. Start Infrastructure Services
```bash
# Start PostgreSQL, Redis, Kafka, and Zookeeper
docker-compose up postgres redis zookeeper kafka -d

# Wait for services to be ready
docker-compose logs -f postgres kafka
```

### 4. Initialize Database
```bash
# Create database tables
python scripts/setup_database.py
```

### 5. Setup Kafka Topics
```bash
# Create required Kafka topics
python scripts/setup_kafka.py
```

### 6. Start the Application
```bash
# Terminal 1: Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start the Kafka consumer
python scripts/run_kafka_consumer.py
```

### 7. Verify Installation
```bash
# Check API health
curl http://localhost:8000/health

# Get latest price (this will trigger the full pipeline)
curl "http://localhost:8000/api/v1/prices/latest?symbol=AAPL"

# Check moving average (after getting 5+ price points)
curl "http://localhost:8000/api/v1/prices/moving-average/AAPL"
```

## 📚 API Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs

The API provides endpoints for:
- Market data retrieval (latest prices, historical data)
- Moving averages calculation
- Polling job management
- System health monitoring

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key | - | Yes |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka server addresses | `localhost:9092` | No |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` | No |
| `DEFAULT_PROVIDER` | Default market data provider | `alpha_vantage` | No |
| `CACHE_TTL` | Cache time-to-live (seconds) | `300` | No |

### Market Data Providers

#### Alpha Vantage
- **Rate Limit**: 5 calls per minute (free tier)
- **Setup**: Get free API key from [alphavantage.co](https://www.alphavantage.co/support/#api-key)
- **Symbols**: US stocks (AAPL, MSFT, GOOGL, etc.)

#### Future Providers
- Yahoo Finance (`yfinance`)
- Finnhub (free tier)

## 🗄️ Database Schema

### Tables

#### `raw_market_data`
Stores complete API responses for audit trail.
```sql
- id (UUID, Primary Key)
- symbol (String, Indexed)
- provider (String)  
- raw_response (JSONB)
- timestamp (DateTime, Indexed)
- created_at (DateTime)
```

#### `processed_price_points`
Extracted and normalized price data.
```sql
- id (UUID, Primary Key)
- symbol (String, Indexed)
- price (Float)
- timestamp (DateTime, Indexed)
- provider (String)
- raw_response_id (UUID, Foreign Key)
- created_at (DateTime)
```

#### `moving_averages`
Calculated moving averages for different periods.
```sql
- id (UUID, Primary Key)
- symbol (String, Indexed)
- moving_average (Float)
- period (Integer)
- timestamp (DateTime, Indexed)
- created_at (DateTime)
```

#### `polling_job_configs`
Persistent polling job configurations.
```sql
- id (UUID, Primary Key)
- job_id (String, Unique)
- symbols (JSONB)
- interval (Integer)
- provider (String)
- status (String)
- created_at, updated_at (DateTime)
- last_run, next_run (DateTime)
- error_message (Text)
```

## 📨 Kafka Integration

### Topics

#### `price-events`
Raw price updates from market data APIs.

**Message Schema:**
```json
{
  "symbol": "AAPL",
  "price": 196.45,
  "timestamp": "2025-06-14T18:05:48.660453",
  "source": "alpha_vantage",
  "raw_response_id": "uuid-here"
}
```

#### `symbol_averages`
Calculated moving averages from consumers.

**Message Schema:**
```json
{
  "symbol": "AAPL",
  "moving_average": 195.82,
  "period": 5,
  "timestamp": "2025-06-14T18:05:48.660453",
  "calculated_at": "2025-06-14T18:05:50.123456"
}
```

### Consumer Groups
- `moving-average-calculator`: Processes price events and calculates moving averages

## 📝 API Testing

### Postman Collection

A comprehensive Postman collection is provided to help test and interact with the API endpoints. The collection includes:

- Health check endpoints
- Price data retrieval endpoints
- Moving average endpoints
- Polling job management endpoints

#### Using the Collection

1. Import the collection into Postman:
   - File → Import → Select `docs/postman_collection.json`

2. Set up environment variables:
   - Create a new environment in Postman
   - Add variable `base_url` with value `http://localhost:8000`

3. Run API tests:
   - Get system health: `GET /health`
   - Get latest price: `GET /api/v1/prices/latest?symbol=AAPL`
   - Start polling job: `POST /api/v1/prices/poll`
   - Check job status: `GET /api/v1/prices/poll/{job_id}`

The collection includes pre-configured requests with appropriate headers, query parameters, and request bodies.

### Project Structure
```
market-data-service/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   └── prices.py          # Price API endpoints
│   │   └── dependencies.py        # FastAPI dependencies
│   ├── core/
│   │   ├── config.py              # Configuration settings
│   │   └── database.py            # Database connection
│   ├── models/
│   │   └── database.py            # SQLAlchemy models
│   ├── services/
│   │   ├── market_data.py         # Market data service
│   │   ├── data_access.py         # Database operations
│   │   ├── kafka_producer.py      # Kafka message producer
│   │   ├── kafka_consumer.py      # Kafka message consumer
│   │   └── providers/
│   │       ├── base.py            # Provider interface
│   │       └── alpha_vantage.py   # Alpha Vantage provider
│   ├── schemas/
│   │   └── prices.py              # Pydantic schemas
│   └── main.py                    # FastAPI application
├── scripts/
│   ├── setup_database.py         # Database initialization
│   ├── setup_kafka.py            # Kafka topic creation
│   └── run_kafka_consumer.py     # Consumer runner
├── requirements/
│   ├── base.txt                   # Production dependencies
│   └── dev.txt                    # Development dependencies
├── docker-compose.yml            # Infrastructure services
├── .env.example                  # Environment template
└── README.md                     # This file
```

## 🧪 Testing

### Test Suite

The project includes a comprehensive test suite with different levels of testing:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between components
- **Functional Tests**: End-to-end tests of the complete pipeline

### Running Tests

```bash
# Install development dependencies
pip install -r requirements/dev.txt

# Run all tests
python scripts/run_tests.py --type all

# Run specific test types
python scripts/run_tests.py --type unit
python scripts/run_tests.py --type integration
python scripts/run_tests.py --type functional

# Run with increased verbosity
python scripts/run_tests.py --type unit -v
```

### Test Coverage

Generate a test coverage report:

```bash
pytest --cov=app tests/
```

### Continuous Integration

Tests are automatically run on every pull request and push to the main branch using GitHub Actions.