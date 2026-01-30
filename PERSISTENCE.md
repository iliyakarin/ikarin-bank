# Database Persistence Configuration

## Overview
All database services are now configured to persist data to the `./data/` directory. This ensures that data survives container restarts and recreations.

## Persistent Volumes

### 1. **PostgreSQL** (`./data/postgres/`)
- **Mount Point**: `/var/lib/postgresql/data`
- **Purpose**: Stores all user accounts, transactions, and banking data
- **Size**: ~4KB (with initialization data)
- **Persistence**: User data survives container restarts ✅

### 2. **ClickHouse** (`./data/clickhouse/`)
- **Mount Point**: `/var/lib/clickhouse`
- **Purpose**: Stores analytics, metrics, and transaction ledger data
- **Size**: ~52KB (with schema and data)
- **Persistence**: Analytics data survives container restarts ✅

### 3. **Kafka** (`./data/kafka/`)
- **Mount Point**: `/var/lib/kafka/data`
- **Purpose**: Stores Kafka broker logs and message data
- **Size**: ~636KB (with message topics and consumer offsets)
- **Persistence**: Topic configuration and message history survives restarts ✅

### 4. **Zookeeper** (`./data/zookeeper/`)
- **Mount Point**: `/var/lib/zookeeper` and `/var/log/zookeeper`
- **Purpose**: Stores cluster coordination state and logs
- **Size**: ~8KB (with coordination data)
- **Persistence**: Cluster state survives container restarts ✅

## Data Isolation Benefits

With persistent storage configured:
- **No data loss** during container restarts or updates
- **Reproducible environments** - can stop/start containers without losing state
- **Easy debugging** - data available after container crashes
- **Development parity** - local development matches production persistence behavior
- **Backup friendly** - entire `./data/` directory can be backed up

## Usage

### Starting Services with Persistence
```bash
docker-compose up -d
# All data automatically persists to ./data/
```

### Stopping Services (Data Persists)
```bash
docker-compose down
# Data in ./data/ is preserved
```

### Cleaning Persistent Data
```bash
rm -rf ./data/*
docker-compose down -v
docker-compose up -d
# Fresh start with clean data
```

## Directory Structure
```
data/
├── postgres/              # PostgreSQL data files
│   └── pgdata
├── clickhouse/            # ClickHouse data files
│   ├── data/
│   ├── metadata/
│   └── store/
├── kafka/                 # Kafka broker logs
│   └── kafka-logs-*/
└── zookeeper/             # Zookeeper coordination
    ├── version-2/
    └── datalog/
```

## Verification

To verify persistence is working:

1. **Create a transaction**:
   ```bash
   # Login and transfer money
   ```

2. **Stop containers**:
   ```bash
   docker-compose down
   ```

3. **Start containers**:
   ```bash
   docker-compose up -d
   ```

4. **Verify data**:
   ```bash
   # Query PostgreSQL - user data should still exist
   # Query ClickHouse - transaction history should be preserved
   # Kafka topics should still exist
   ```

## Performance Considerations

- **PostgreSQL**: Named volumes provide good I/O performance
- **ClickHouse**: Using ReplacingMergeTree engine for efficient storage
- **Kafka**: Local storage is fast for single-broker setup
- **Zookeeper**: Minimal overhead with fast coordination

## Notes

- Data files are owned by container users (UID/GID)
- Direct access to data files requires elevated permissions
- Backup entire `./data/` directory for disaster recovery
- For production, consider using cloud storage backends or replication
