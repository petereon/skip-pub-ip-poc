# P2P NAT Traversal - Protobuf Architecture

Complete rewrite with simplified protobuf-based bidirectional messaging.

## ✨ New Architecture

### What Changed

**Before**: HTTP-based with separate proxy binaries
**Now**: Protobuf-based with unified node binary

**Rust Side**:
- Single binary: `p2p-node`
- Two modes: `--mode server` or `--mode client`
- Two functions: `send()` and `listen()`
- Communication via stdin/stdout with Python

**Python Side**:
- `p2p_server.py` - Spawns Rust node, sends/receives messages
- `p2p_client.py` - Spawns Rust node, sends/receives messages
- Simple protobuf messages (JSON for demo)

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

### Rust Functions

**send(peer_id, message)** - Send protobuf message
```bash
send <peer_id> {"type": "request", "payload": "hello"}
```

**listen()** - Automatically receives messages (printed to stdout)

### Python API

**Server**:
```python
server = P2PServer()
await server.start()
await server.send_message(peer_id, message)
```

**Client**:
```python
client = P2PClient()
await client.start()
await client.send_message(message)  # Goes to discovered server
```

## 📦 Message Format

Protobuf schema (proto/message.proto):
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

## 🔧 How It Works

1. **Python starts Rust subprocess**: `cargo run --bin p2p-node`
2. **Rust handles P2P**: DHT, NAT traversal, connections
3. **Python sends commands via stdin**: `send <peer> <message>`
4. **Rust outputs to stdout**: Messages received, status updates
5. **Bidirectional**: Both sides can send anytime

See [QUICKSTART_V2.md](QUICKSTART_V2.md) for detailed guide.
