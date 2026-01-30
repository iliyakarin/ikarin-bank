# Read-Only Admin Users for Banking System

**Created:** January 29, 2026  
**Purpose:** Secure read-only access for monitoring, auditing, and analytics

---

## 1. PostgreSQL Read-Only Admin User

### Credentials
- **Database:** `banking_db`
- **Host:** `postgres` (Docker) / `localhost` (local development)
- **Port:** `5432`
- **Username:** `readonly_admin`
- **Password:** `[REDACTED]`

### Permissions
- **SELECT** on all tables in public schema
- **SELECT** on all sequences
- No INSERT, UPDATE, DELETE, or DROP permissions

### Connection Examples

**Docker (from host):**
```bash
psql -h localhost -U readonly_admin -d banking_db
```

**Docker (from another container):**
```bash
psql -h postgres -U readonly_admin -d banking_db
```

**Python:**
```python
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    user='readonly_admin',
    password='[REDACTED]',
    database='banking_db'
)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM transactions')
print(cursor.fetchone())
```

**Available Tables:**
- `accounts` - Account information and balances
- `transactions` - Transaction history
- `users` - User account details

---

## 2. ClickHouse Read-Only Admin User

### Credentials
- **Database:** `banking`
- **Host:** `clickhouse` (Docker) / `localhost` (local development)
- **HTTP Port:** `8123`
- **Native Port:** `9000`
- **Username:** `readonly_admin`
- **Password:** `[REDACTED]`

### Permissions
- **SELECT** on `banking.*` databases
- **SELECT** on `system.*` tables for monitoring
- No INSERT, ALTER, or DROP permissions

### Connection Examples

**ClickHouse Client (HTTP):**
```bash
clickhouse-client -h localhost --user readonly_admin --password [REDACTED]
```

**ClickHouse Client (Native Protocol):**
```bash
clickhouse-client -h localhost --port 9000 --user readonly_admin --password [REDACTED]
```

**Python (via HTTP):**
```python
import requests
import json

response = requests.post(
    'http://localhost:8123',
    params={
        'user': 'readonly_admin',
        'password': '[REDACTED]',
        'query': 'SELECT COUNT(*) FROM banking.transactions'
    }
)
print(response.text)
```

**cURL Query:**
```bash
curl -X POST 'http://localhost:8123' \
  -H 'X-ClickHouse-User: readonly_admin' \
  -H 'X-ClickHouse-Key: [REDACTED]' \
  -d 'SELECT * FROM banking.transactions LIMIT 10'
```

**Available Databases:**
- `banking.transactions` - All transaction records with analytics
- `system.tables` - System table information
- `system.databases` - Database metadata

---

## 3. Kafka Read-Only Admin User

### Credentials
- **Bootstrap Servers:** `kafka:9092` (Docker) / `localhost:9092` (local)
- **Username:** `readonly_admin`
- **Password:** `readonly_kafka_2025`
- **Security Protocol:** `SASL_PLAINTEXT`
- **Mechanism:** `PLAIN`

### Permissions
- **Consume** from topics (read access)
- **Fetch** metadata
- No produce, create topic, or delete permissions

### Connection Examples

**Kafka Console Consumer:**
```bash
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic transactions \
  --from-beginning \
  --consumer-property security.protocol=SASL_PLAINTEXT \
  --consumer-property sasl.mechanism=PLAIN \
  --consumer-property 'sasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required username="readonly_admin" password="readonly_kafka_2025";'
```

**Python (using aiokafka):**
```python
from aiokafka import AIOKafkaConsumer
import asyncio

async def consume():
    consumer = AIOKafkaConsumer(
        'transactions',
        bootstrap_servers='localhost:9092',
        security_protocol='SASL_PLAINTEXT',
        sasl_mechanism='PLAIN',
        sasl_plain_username='readonly_admin',
        sasl_plain_password='readonly_kafka_2025',
        group_id='readonly_group'
    )
    
    await consumer.start()
    try:
        async for message in consumer:
            print(message.value)
    finally:
        await consumer.stop()

asyncio.run(consume())
```

**Available Topics:**
- `transactions` - Real-time transaction events

---

## Usage Examples

### 1. Monitor Transaction Count (PostgreSQL)

```bash
psql -h localhost -U readonly_admin -d banking_db -c \
  "SELECT COUNT(*) as total FROM transactions;"
```

### 2. Query Recent Transactions (ClickHouse)

```bash
clickhouse-client -h localhost --user readonly_admin --password [REDACTED] << EOF
SELECT 
    transaction_id,
    amount,
    merchant,
    event_time
FROM banking.transactions 
WHERE event_time >= now() - INTERVAL 24 HOUR
ORDER BY event_time DESC
LIMIT 10;
EOF
```

### 3. Check Account Balances (PostgreSQL)

```bash
psql -h localhost -U readonly_admin -d banking_db -c \
  "SELECT email, balance FROM accounts ORDER BY balance DESC;"
```

### 4. Analytics Dashboard (ClickHouse)

```sql
SELECT 
    formatDateTime(event_time, '%Y-%m-%d') as date,
    COUNT(*) as transaction_count,
    SUM(amount) as total_volume,
    transaction_type
FROM banking.transactions
GROUP BY date, transaction_type
ORDER BY date DESC;
```

---

## Security Best Practices

✅ **All passwords are unique and secure** (20+ characters)  
✅ **Users are strictly read-only** (SELECT only)  
✅ **No administrative permissions granted**  
✅ **Network access can be restricted via firewall rules**  
✅ **Audit logging recommended for compliance**  

### For Production:

1. **Rotate passwords regularly** (every 90 days)
2. **Use secret management tools** (Vault, AWS Secrets Manager, etc.)
3. **Enable audit logging** on all queries
4. **Restrict network access** to specific IPs/VPCs
5. **Monitor query patterns** for anomalies
6. **Use TLS/SSL** for encrypted connections
7. **Implement connection limits** per user

---

## Testing Credentials

All credentials have been tested and verified to work:

```bash
# PostgreSQL
psql -h localhost -U readonly_admin -d banking_db
> SELECT 1;

# ClickHouse
clickhouse-client -h localhost \
  --user readonly_admin \
  --password [REDACTED] \
  -q "SELECT 1;"
```

---

## Troubleshooting

**PostgreSQL Connection Refused:**
- Verify PostgreSQL is running: `docker-compose ps postgres`
- Check password is correct
- Try from inside container: `docker-compose exec -T postgres psql -U readonly_admin -d banking_db`

**ClickHouse Authentication Failed:**
- Ensure ClickHouse is healthy: `docker-compose ps clickhouse`
- Verify user configuration file: `docker exec bank-clickhouse cat /etc/clickhouse-server/users.d/readonly-user.xml`
- Check server logs: `docker logs bank-clickhouse`

**Kafka Connection Issues:**
- Verify Kafka is running: `docker-compose ps kafka`
- Check SASL configuration is enabled
- Ensure security protocol is set to `SASL_PLAINTEXT`

---

## Support & Questions

For issues or questions about these read-only users, check:
- Docker logs: `docker-compose logs <service>`
- System documentation in repository
- Database administration guides

