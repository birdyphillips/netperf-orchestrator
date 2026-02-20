from kafka import KafkaConsumer
import time
import argparse

parser = argparse.ArgumentParser(description='Kafka consumer for CM metrics')
parser.add_argument('--mac', type=str, default='e0db.d161.3d18', help='Cable modem MAC address (format: e0db.d161.3d18 or a0:ed:6d:9f:4b:74)')
args = parser.parse_args()

# Normalize MAC address format
CM_MAC = args.mac.replace(':', '').replace('.', '').lower()
CM_MAC_COLON = ':'.join([CM_MAC[i:i+2] for i in range(0, 12, 2)])

print(f"Listening for cmMacAddr=\"{CM_MAC_COLON}\",dir=\"downstream\" metrics...")
while True:
    try:
        consumer = KafkaConsumer(
            'cmts_metrics_apc01k1dccc',
            bootstrap_servers='kafka01.daas.charterlab.com:9092',
            group_id=f'metrics-consumer-{int(time.time())}',
            auto_offset_reset='latest',
            enable_auto_commit=True,
            consumer_timeout_ms=1000
        )
        
        for message in consumer:
            try:
                msg = message.value.decode('utf-8')
                if f'cmMacAddr="{CM_MAC_COLON}"' in msg and 'dir="downstream"' in msg:
                    print(msg)
            except:
                pass
        consumer.close()
    except KeyboardInterrupt:
        print("\nStopped")
        break
    except:
        pass
