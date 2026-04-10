from kafka import KafkaConsumer, TopicPartition
import time
import argparse

#BROKER = '96.37.182.148:9092'  # kafka01.daas.charterlab.com
BROKER = '65.185.232.139:11203' #stamp-kafka-brk.stage.charterlab.com:11203
DEFAULT_TOPIC = 'cmts_metrics_apc01k1dccc'

parser = argparse.ArgumentParser(description='Kafka consumer for CM metrics')
parser.add_argument('--mac', type=str, default=None, help='Filter by cable modem MAC address')
parser.add_argument('--broker', type=str, default=BROKER, help=f'Kafka broker (default: {BROKER})')
parser.add_argument('--topic', type=str, default=DEFAULT_TOPIC, help=f'Kafka topic (default: {DEFAULT_TOPIC})')
parser.add_argument('--latest', action='store_true', help='Only read new messages (default: read from beginning)')
parser.add_argument('--list-topics', action='store_true', help='List cmts/rxmer/system topics with message counts')
parser.add_argument('--last-message', action='store_true', help='Show timestamp of last message per topic')
parser.add_argument('--filter', type=str, default=None, help='Filter messages containing this string (case-insensitive)')
parser.add_argument('--debug', action='store_true', help='Show sample messages for debugging')
args = parser.parse_args()

if args.last_message:
    from datetime import datetime
    topic = args.topic
    print(f"Checking last message on '{topic}'...")
    c = KafkaConsumer(bootstrap_servers=args.broker)
    partitions = c.partitions_for_topic(topic)
    if not partitions:
        print("  No partitions found.")
        c.close()
        exit(0)
    tps = [TopicPartition(topic, p) for p in partitions]
    c.assign(tps)
    end_offsets = c.end_offsets(tps)
    for tp in tps:
        if end_offsets[tp] == 0:
            print(f"  Partition {tp.partition}: empty")
            continue
        c.seek(tp, end_offsets[tp] - 1)
        msg = next(c)
        ts = datetime.fromtimestamp(msg.timestamp / 1000)
        print(f"  Partition {tp.partition}: last message at {ts} (offset {msg.offset})")
        try:
            print(f"    Preview: {msg.value.decode('utf-8')[:300]}")
        except:
            print(f"    (binary data, {len(msg.value)} bytes)")
    c.close()
    exit(0)

if args.list_topics:
    print(f"Connecting to {args.broker}...")
    c = KafkaConsumer(bootstrap_servers=args.broker)
    topics = sorted(t for t in c.topics() if any(k in t.lower() for k in ['cmts_metrics', 'rxmer_metrics', 'system_metrics', 'daa_cmts', 'consolidated']))
    print(f"\nFound {len(topics)} metric topics:")
    for t in topics:
        partitions = c.partitions_for_topic(t)
        if partitions:
            tps = [TopicPartition(t, p) for p in partitions]
            c.assign(tps)
            end = c.end_offsets(tps)
            begin = c.beginning_offsets(tps)
            total = sum(end[tp] - begin[tp] for tp in tps)
            print(f"  {t}: {total} messages")
        else:
            print(f"  {t}: no partitions")
    c.close()
    exit(0)

filter_mac = args.mac is not None
if filter_mac:
    CM_MAC = args.mac.replace(':', '').replace('.', '').lower()
    CM_MAC_COLON = ':'.join([CM_MAC[i:i+2] for i in range(0, 12, 2)])
    CM_MAC_DOT = '.'.join([CM_MAC[i:i+4] for i in range(0, 12, 4)])

offset_reset = 'latest' if args.latest else 'earliest'

print(f"Connecting to Kafka topic '{args.topic}' (offset: {offset_reset})...")
consumer = KafkaConsumer(
    args.topic,
    bootstrap_servers=args.broker,
    group_id=f'metrics-consumer-{int(time.time())}',
    auto_offset_reset=offset_reset,
    enable_auto_commit=True,
    consumer_timeout_ms=30000
)

if filter_mac:
    print(f"Connected. Filtering for MAC: {CM_MAC_COLON} / {CM_MAC_DOT} / {CM_MAC}")
else:
    print(f"Connected. Printing ALL messages (use --mac to filter)")

msg_count = 0
match_count = 0
try:
    while True:
        for message in consumer:
            msg_count += 1
            try:
                msg = message.value.decode('utf-8')
                msg_lower = msg.lower()
                mac_match = not filter_mac or any(m in msg_lower for m in (CM_MAC, CM_MAC_COLON, CM_MAC_DOT))
                filter_match = not args.filter or args.filter.lower() in msg_lower
                if mac_match and filter_match:
                    match_count += 1
                    print(f"\n[MATCH #{match_count}] {msg[:500]}")
                elif args.debug and msg_count <= 5:
                    print(f"\n[SAMPLE msg #{msg_count}] {msg[:300]}")
            except:
                pass

        print(f"  Consumer timeout - processed {msg_count} messages, {match_count} matches. Reconnecting...")
except KeyboardInterrupt:
    print(f"\nStopped. Total: {msg_count} messages, {match_count} matches")
finally:
    consumer.close()
