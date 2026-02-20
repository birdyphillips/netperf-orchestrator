from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='kafka01.daas.charterlab.com:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

topic = 'cmts_metrics_apc01k1dccc'

# Send message
message = {'key': 'value'}
producer.send(topic, message)
producer.flush()
print(f"Message sent to topic: {topic}")
producer.close()
