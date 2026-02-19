from confluent_kafka import Consumer
import os

conf = {
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'dumper',
    'auto.offset.reset': 'earliest',
    'sasl.mechanisms': 'PLAIN',
    'security.protocol': 'SASL_PLAINTEXT',
    'sasl.username': 'admin',
    'sasl.password': 'admin123'
}

consumer = Consumer(conf)
consumer.subscribe(['bank_transactions'])

print("Dumping last 5 messages:")
msgs = []
try:
    for _ in range(100): # Try more to find recent ones
        msg = consumer.poll(1.0)
        if msg is None: break
        if msg.error(): continue
        msgs.append(msg.value().decode('utf-8'))
except:
    pass

for m in msgs[-5:]:
    print(m)
consumer.close()
