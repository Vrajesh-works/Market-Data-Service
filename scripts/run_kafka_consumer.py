
import sys
import os
import signal
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.kafka_consumer import moving_average_consumer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    logger.info("Received shutdown signal, stopping consumer...")
    moving_average_consumer.stop_consuming()
    sys.exit(0)


def main():
    logger.info("Starting Kafka Moving Average Consumer...")
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        moving_average_consumer.start_consuming()
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()