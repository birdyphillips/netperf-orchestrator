from kafka import KafkaConsumer

consumer = KafkaConsumer(bootstrap_servers='kafka01.daas.charterlab.com:9092')
topics = consumer.topics()
consumer.close()

print("Available topics:")
for topic in sorted(topics):
    print(f"  {topic}")
