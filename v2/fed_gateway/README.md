# FedGateway V2 Architecture

This directory contains the high-fidelity simulation of a **FedLine Direct** host node, implementing the **ISO 20022** messaging standard for real-time gross settlement (RTGS) and instant payments via FedNow.

## Components

### 1. Transport Layer (`v2/fed_gateway/transport/`)
- **`mq_client.py`**: Implements a simulated **IBM MQ** network socket. It provides asynchronous message ingestion, correlation ID management, and asynchronous retrieval using `asyncio.Queue`.

### 2. Messaging Layer (`v2/fed_gateway/parsers/`)
- **`iso20022.py`**: Handles the serialization and deserialization of ISO 20022 XML payloads. 
    - Supports `pacs.008` (Customer Credit Transfer).
    - Supports `pacs.002` (Payment Status Report).
    - Supports `camt.053` (Bank Statement).

### 3. Settlement Engine (`v2/fed_gateway/engine/`)
- **`settlement.py`**: The core business logic.
    - **Fedwire Service**: Processes `pacs.008` transactions with real-time reserve deduction.
    - **Overdraft Controls**: Enforces-daylight overdraft protection. If the simulated Federal Reserve account balance (`reserves`) is insufficient for a transaction, it generates a `pacs.002` rejection (`RJCT`).
    - **FedNow Simulation**: Handles asynchronous status updates.
    - **Liquidity Management**: Generates `camt.053` statements representing the current state of the bank's reserves.

### 4. Orchestrator (`v2/fed_gateway/gateway.py`)
- **`gateway.py`**: The main entry point. It manages the processing loop, routing incoming MQ messages to the `SettlementEngine`, and dispatching the resulting ISO 20022 responses back to the network.

## Communication Protocol

The system uses **ISO 20022 XML** payloads over an asynchronous MQ-like transport.

- **Transaction Request (`pacs.008`)**: Initiates a fund transfer.
- **Transaction Response (`pacs.002`)**: Communics the outcome (`ACCP` for accepted, `RJCT` for rejected).
- **Statement Request (`camt.053` trigger)**: Triggers the generation of a bank statement.

## Testing

Integration tests are located in `tests/v2/fed_gateway/tests/v2/fed_gateway/test_e2e.py`. They verify:
- Successful end-to-end payment processing.
- Correct rejection handling when reserves are insufficient.
- Successful bank statement generation.
