# Client Bank Simulator

This module simulates a commercial bank interacting with the `FedGatewayHost` via the `v2/fed_gateway`-compatible network.

## Capabilities

- **Payment Execution**: Sends `pacs.008` messages to the Federal Reserve and waits for a `pacs.002` (Accept/Reject) response.
- **Statement Retrieval**: Triggers the generation of `camt.05_3` bank statements.
- **Protocol Abstraction**: Uses a high-level `ClientMQWrapper` to abstract the complex XML and MQ transport logic.

## Architecture

The simulator uses a service-oriented approach:
1.  **`ClientBankService`**: High-level business logic (e.g., `execute_payment`).
2.  **`ClientMQWrapper`**: A lightweight wrapper over `MQClient` to simplify the ISO 20022 messaging lifecycle.

## Usage

The service can be used as a library or within integration tests to simulate a bank's behavior during a clearing window.
