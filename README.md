# Quick Start Guide - Protobuf Version

## New Simplified Architecture

```
Client Network (NAT)              Server Network (NAT)
┌─────────────────┐              ┌─────────────────┐
│ p2p_client.py   │              │ p2p_server.py   │
│ (send/listen)   │              │ (send/listen)   │
└────────┬────────┘              └────────┬────────┘
         │ stdin/stdout                   │ stdin/stdout
         │                                │
┌────────▼────────┐              ┌────────▼────────┐
│  p2p-node       │              │  p2p-node       │
│  (Rust)         │◄────P2P─────►│  (Rust)         │
│  --mode client  │  Protobuf    │  --mode server  │
│  send()         │  Messages    │  send()         │
│  listen()       │  over        │  listen()       │
└─────────────────┘  libp2p      └─────────────────┘
```

## Setup

```bash
# Install dependencies
cargo build --bin p2p-node
pip install -e .
```

## Running

### Server Side (e.g., Raspberry Pi)

```bash
python3 p2p_server.py
```

That's it! The Python script starts the Rust node automatically.

### Client Side (anywhere else)

```bash
python3 p2p_client.py
```

Then type messages to send to the server!

## How It Works

### Rust Side (p2p-node)

Two simple functions:
- **`send(peer_id, message)`** - Send protobuf message to peer
- **`listen()`** - Receive messages from peers

Commands via stdin:
```
send <peer_id> <json_message>
list
```

### Python Side

**Server** (p2p_server.py):
```python
server = P2PServer()
await server.start()  # Starts Rust node
await server.send_message(peer_id, message)
```

**Client** (p2p_client.py):
```python
client = P2PClient()
await client.start()  # Starts Rust node, finds server
await client.send_message(message)
```

## Message Format

Protobuf schema:
```protobuf
message Message {
  string id = 1;
  string type = 2;
  bytes payload = 3;
  int64 timestamp = 4;
  map<string, string> metadata = 5;
}
```

Python usage:
```python
msg = Message.create(
    msg_type="request",
    payload="hello world",
    metadata={"key": "value"}
)
```

## Testing

```bash
# Terminal 1 - Server
python3 p2p_server.py

# Terminal 2 - Client
python3 p2p_client.py

# In client, type messages:
Message: hello server!
Message: test message
```

## Advantages

1. **Simpler** - No HTTP, just send/receive
2. **Faster** - Binary protobuf, no HTTP overhead
3. **Bidirectional** - Server can message clients too
4. **Cleaner** - Rust handles all P2P, Python just messaging logic
5. **Type-safe** - Protobuf schema validation

## Next Steps

- [ ] Add proper protobuf compilation (protoc)
- [ ] Implement actual stream handling in Rust
- [ ] Add message acknowledgments
- [ ] Add broadcast to multiple peers
- [ ] Add encryption/authentication
