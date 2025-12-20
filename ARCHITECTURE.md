# P2P NAT Traversal - Transport-Agnostic Architecture

Simplified architecture with clean separation of concerns.

## ✨ Architecture Principles

### Separation of Concerns

**Rust (p2p-node)**: Transport layer only
- Handles P2P networking (libp2p, DHT, NAT traversal)
- Works with raw bytes (`Vec<u8>`)
- Doesn't know about message formats

**Python (p2p_server.py / p2p_client.py)**: Application layer
- Handles message serialization (JSON for PoC)
- Can switch to protobuf/msgpack without touching Rust
- Contains business logic

### Communication Flow

```
Python App ─(JSON)─> encode ─(bytes)─> stdin ─> Rust ─(P2P)─> Network
                                                         ^
                                                         │
Python App <─(JSON)─ decode <─(bytes)─ stdout <─ Rust <─┘
```

## 🚀 Quick Start

```bash
# Build Rust node
cargo build --bin p2p-node

# Terminal 1 - Server
python3 p2p_server.py

# Terminal 2 - Client
python3 p2p_client.py
```

Type messages in client to send to server!

## 📡 API

### Rust Interface (stdin/stdout)

**Input (stdin)**:
```bash
send <peer_id> <json_string>
list
```

**Output (stdout)**:
- Status messages (connection events, errors)
- Received messages (in future: JSON from peers)

### Python API

**Server**:
```python
server = P2PServer()
await server.start()
await server.send_message(peer_id, {"type": "msg", "data": "hello"})
```

**Client**:
```python
client = P2PClient()
await client.start()
await client.send_message({"type": "request", "payload": "hello"})
```

## 📦 Message Format

Simple JSON for PoC:
```json
{
  "type": "request",
  "payload": "hello world",
  "metadata": {"from": "python_client"},
  "timestamp": 1234567890.123
}
```

Easy to switch to:
- Protobuf (binary, type-safe)
- MessagePack (binary, fast)
- CBOR (binary, self-describing)
- Any other format

## 🔧 How It Works

1. **Python starts Rust subprocess**: `cargo run --bin p2p-node --mode client`
2. **Rust handles P2P**: DHT lookup, NAT traversal, connections
3. **Python sends JSON via stdin**: Encodes dict → JSON → bytes → stdin
4. **Rust transports bytes**: Sends raw bytes over libp2p
5. **Rust outputs to stdout**: Received bytes → stdout
6. **Python decodes**: bytes → JSON → dict
7. **Bidirectional**: Both sides can send anytime

## 🎯 Why This Design?

**Before**: Rust knew about protobuf → tight coupling
**Now**: Rust handles bytes → Python handles serialization

**Benefits**:
- Switch serialization formats without recompiling Rust
- Easier testing (send raw bytes)
- Cleaner code boundaries
- Python stays simple (no protobuf deps for PoC)
- Can add multiple Python clients with different formats
