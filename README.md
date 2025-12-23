# Skip Public IP - P2P WebSocket with DHT & Hole Punching

A proof-of-concept demonstrating **BitTorrent-style NAT traversal** for WebSocket connections. Uses the BitTorrent DHT for peer discovery and TCP hole punching to establish direct connections without port forwarding or public IP addresses.

## 🎯 The Goal

Enable two peers behind NAT to establish a WebSocket connection **without**:
- ❌ Port forwarding
- ❌ Router configuration
- ❌ Public IP addresses
- ❌ Central relay servers

## 🔧 How It Works

### 1. **BitTorrent DHT for Discovery**
- Server announces its local & external endpoints to the global BitTorrent DHT
- Client retrieves peer information using a hash
- No central server needed - fully distributed

### 2. **TCP Hole Punching for NAT Traversal**
- Both peers simultaneously attempt to connect to each other
- Creates temporary NAT mappings that allow packets through
- Same technique used by BitTorrent, Skype, and other P2P applications

### 3. **WebSocket for Application Protocol**
- Once TCP connection established, upgrade to WebSocket
- Familiar API for building applications

## 🚀 Quick Start

### Install Dependencies

```bash
# Install Rust (required for mainline DHT library)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install Python dependencies
pip install maturin websockets aiohttp

# Build the Rust-Python bridge
maturin develop
```

### Run the Server

```bash
python ws_server.py
```

You'll see output like:
```
✅ Registered my-websocket-service in BitTorrent DHT
   Hash: Id(fa1585b6db7f8ff89bfa0a2d5361a9d8c52656ac)

📋 COPY THIS HASH FOR THE CLIENT:
   Id(fa1585b6db7f8ff89bfa0a2d5361a9d8c52656ac)
```

### Run the Client (from another network!)

```bash
python ws_client.py "Id(fa1585b6db7f8ff89bfa0a2d5361a9d8c52656ac)"
```

The client will:
1. Find the server via DHT
2. Attempt TCP hole punching
3. Establish WebSocket connection
4. Exchange messages

## 📁 Project Structure

```
├── src/lib.rs           # Rust DHT wrapper (PyO3)
├── holepunch.py         # TCP hole punching implementation
├── ws_server.py         # WebSocket server with DHT registration
├── ws_client.py         # WebSocket client with hole punching
├── HOLEPUNCH.md         # Detailed explanation of hole punching
└── pyproject.toml       # Python dependencies
```

## 🧪 Testing Scenarios

### Same Network
Both peers are on the same LAN:
- ✅ Uses local IP addresses
- ✅ Direct connection (no hole punching needed)

### Different Networks (Typical NAT)
Peers are on different networks with standard home routers:
- ✅ Uses TCP hole punching
- ✅ Works with Full Cone, Restricted Cone, Port-Restricted NAT
- ⚠️ May fail with Symmetric NAT (~20% of cases)

### Firewall/Symmetric NAT
Corporate networks or strict NAT:
- ⚠️ Falls back to direct connection attempt
- ❌ May require port forwarding or relay server

## 🔍 Technical Details

### BitTorrent DHT
- **Distributed**: No central authority
- **Mainline DHT**: Uses the official BitTorrent network (millions of nodes)
- **Immutable storage**: Content-addressed data storage
- **Hash-based lookup**: SHA-1 hash of service data

### TCP Hole Punching
- **SO_REUSEADDR**: Allows multiple sockets on same port
- **Simultaneous Open**: Both peers connect to each other at once
- **Port Preservation**: Most NATs maintain source port numbers
- **Timing**: DHT coordinates when to start punching

See [HOLEPUNCH.md](HOLEPUNCH.md) for deep dive.

## ⚡ Performance

- **DHT Lookup**: 2-5 seconds typical
- **Hole Punch**: 1-10 seconds depending on NAT
- **Connection**: Direct P2P (no relay overhead)
- **Latency**: Minimal (same as direct connection)

## 🛡️ Limitations

1. **Symmetric NAT**: ~20% success rate (random port allocation)
2. **Carrier-Grade NAT**: May not work (double NAT)
3. **Strict Firewalls**: May block outgoing connections
4. **IPv6**: Not yet implemented
5. **WebSocket Handshake**: Currently uses fallback direct connection

## 🔬 Why This Matters

This demonstrates that **truly decentralized P2P applications are possible** on today's internet:

- **No Infrastructure Costs**: No servers to maintain
- **Privacy**: No third party sees your connections
- **Censorship Resistant**: No central point to shut down
- **Scalability**: More peers = more capacity

Real-world applications:
- P2P file sharing (BitTorrent)
- Video calls (early Skype)
- Gaming (peer-to-peer multiplayer)
- Blockchain networks
- Distributed messaging

## 🚧 Future Improvements

- [ ] WebRTC data channels (better NAT traversal)
- [ ] STUN/TURN fallback servers
- [ ] IPv6 support
- [ ] UPnP/NAT-PMP for automatic port mapping
- [ ] Multiple simultaneous connections (connection pool)
- [ ] Bandwidth optimization
- [ ] Connection quality monitoring

## 📚 Learn More

- [HOLEPUNCH.md](HOLEPUNCH.md) - Detailed hole punching guide
- [RFC 5128](https://tools.ietf.org/html/rfc5128) - P2P Across NATs
- [BitTorrent DHT](http://www.bittorrent.org/beps/bep_0005.html) - Protocol spec
- [Mainline DHT Rust](https://github.com/pubky/mainline) - Library used here

## 📝 License

MIT

## 🤝 Contributing

This is a proof-of-concept. Contributions welcome for:
- Better NAT detection
- More robust hole punching
- WebRTC integration
- Production hardening

## ⚠️ Disclaimer

This is experimental software for educational purposes. Not recommended for production use without extensive testing and security review.
