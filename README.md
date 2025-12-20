# P2P NAT Traversal - Proof of Concept

## Architecture

```
Client Network (NAT)              Server Network (NAT)
┌─────────────────┐              ┌─────────────────┐
│ p2p_client.py   │              │ p2p_server.py   │
│ (JSON encode)   │              │ (JSON encode)   │
└────────┬────────┘              └────────┬────────┘
         │ stdin/stdout                   │ stdin/stdout
         │                                │
┌────────▼────────┐              ┌────────▼────────┐
│  p2p-node       │              │  p2p-node       │
│  (Rust)         │◄────P2P─────►│  (Rust)         │
│  --mode client  │   Raw Bytes  │  --mode server  │
│  send(bytes)    │   over       │  send(bytes)    │
│  listen()       │   libp2p     │  listen()       │
└─────────────────┘              └─────────────────┘
```

**Key Design**: Rust is transport-agnostic, handling only raw bytes. Python handles all serialization (JSON for PoC).

## Setup

```bash
# Build Rust P2P node
cargo build --bin p2p-node

# No Python dependencies needed!
```

## Running

### Server Side (e.g., Raspberry Pi)

```bash
python3 p2p_server.py
```

The Python script starts the Rust node automatically.

### Client Side (anywhere else)

```bash
python3 p2p_client.py
```

Type messages to send to the server!

## How It Works

### Rust Side (p2p-node)

Two simple functions:
- **`send(peer_id, bytes)`** - Send raw bytes to peer
- **`listen()`** - Receive raw bytes from peers

Commands via stdin:
```
send <peer_id> <json_string>
list
```

### Python Side

**Server** (p2p_server.py):
```python
server = P2PServer()
await server.start()  # Starts Rust node
await server.send_message(peer_id, {"type": "msg", "data": "hello"})
```

**Client** (p2p_client.py):
```python
client = P2PClient()
await client.start()  # Starts Rust node, finds server
await client.send_message({"type": "request", "payload": "hello"})
```

## Message Format

Simple JSON for PoC:
```json
{
  "type": "request",
  "payload": "hello world",
  "metadata": {"from": "client"},
  "timestamp": 1234567890.123
}
```

Python handles all encoding/decoding. Rust just transports bytes.

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

1. **Transport-Agnostic** - Rust handles P2P, doesn't care about message format
2. **Simple** - JSON for PoC, easy to switch to protobuf/msgpack later
3. **Faster** - No serialization overhead in Rust
4. **Bidirectional** - Server can message clients too
5. **Cleaner Separation** - Python = app logic, Rust = networking
6. **No Dependencies** - Python has zero external dependencies

## Next Steps

- [ ] Implement actual stream handling in Rust (currently just prints)
- [ ] Add message acknowledgments
- [ ] Add broadcast to multiple peers
- [ ] Switch to protobuf/msgpack for production
- [ ] Add encryption/authentication
- [ ] Handle reconnection logic
