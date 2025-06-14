
import sys
import os
import time
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka import KafkaError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_kafka(admin_client, max_attempts=30, delay=2):
    logger.info("Waiting for Kafka to be ready...")
    
    for attempt in range(max_attempts):
        try:
            # Try to get cluster metadata
            metadata = admin_client.list_topics(timeout=5)
            logger.info("Kafka is ready!")
            return True
        except Exception as e:
            logger.info(f"Attempt {attempt + 1}/{max_attempts}: Kafka not ready ({e}), waiting {delay}s...")
            time.sleep(delay)
    
    return False


def create_topics(admin_client):
    #Create Kafka topics if they don't exist
    
    topics_to_create = [
        NewTopic(
            topic=settings.KAFKA_TOPIC_PRICE_EVENTS,
            num_partitions=3, 
            replication_factor=1  
        ),
        NewTopic(
            topic=settings.KAFKA_TOPIC_SYMBOL_AVERAGES,
            num_partitions=3,
            replication_factor=1
        )
    ]
    
    try:
        existing_topics = admin_client.list_topics(timeout=10).topics.keys()
        logger.info(f"Existing topics: {list(existing_topics)}")
    except Exception as e:
        logger.error(f"Failed to list existing topics: {e}")
        return False
    
    new_topics = []
    for topic in topics_to_create:
        if topic.topic not in existing_topics:
            new_topics.append(topic)
            logger.info(f"Will create topic: {topic.topic}")
        else:
            logger.info(f"Topic already exists: {topic.topic}")
    
    if not new_topics:
        logger.info("All topics already exist")
        return True
    
    try:
        futures = admin_client.create_topics(new_topics)
        
        for topic, future in futures.items():
            try:
                future.result()  # The result itself is None
                logger.info(f"✓ Topic '{topic}' created successfully")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"✓ Topic '{topic}' already exists")
                else:
                    logger.error(f"✗ Failed to create topic '{topic}': {e}")
                    return False
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create topics: {e}")
        return False


def main():
    logger.info("Setting up Kafka topics for Market Data Service...")
    logger.info(f"Kafka servers: {settings.KAFKA_BOOTSTRAP_SERVERS}")
    
    admin_config = {
        'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'client.id': 'kafka-setup'
    }
    
    admin_client = AdminClient(admin_config)
    
    if not wait_for_kafka(admin_client):
        logger.error("Kafka is not ready. Please check your Kafka containers.")
        logger.error("Try: docker-compose logs kafka")
        sys.exit(1)
    
    if create_topics(admin_client):
        logger.info("Kafka setup completed successfully!")
        
        try:
            topics = admin_client.list_topics(timeout=10).topics.keys()
            logger.info(f"Available topics: {sorted(list(topics))}")
        except Exception as e:
            logger.warning(f"Could not list final topics: {e}")
        
    else:
        logger.error("Kafka setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()