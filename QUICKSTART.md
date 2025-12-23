# Quick Start - Manual Hash Discovery

Since automatic DHT discovery requires mutable storage (not yet implemented), use this manual workaround:

## Step 1: Start the Server

```bash
python ws_server.py
```

The server will print output like:
```
✅ Registered my-websocket-service -> ws://localhost:8765 in BitTorrent DHT
   Hash: Id(98928187b2f35fcecb76aa08bcc3303224d7fdd5)
   Stored at 20 nodes

📋 COPY THIS HASH FOR THE CLIENT:
   Id(98928187b2f35fcecb76aa08bcc3303224d7fdd5)
============================================================
```

**Copy the hash!**

## Step 2: Update Client

Edit [ws_client.py](ws_client.py) and paste the hash:

```python
DHT_HASH = "Id(98928187b2f35fcecb76aa08bcc3303224d7fdd5)"  # Paste your hash here
```

Or pass it as a command line argument:

```bash
python ws_client.py "Id(98928187b2f35fcecb76aa08bcc3303224d7fdd5)"
```

## Step 3: Run the Client

```bash
python ws_client.py
```

The client will:
1. Connect to the DHT
2. Retrieve the server info using the hash
3. Connect to the WebSocket server
4. Exchange messages

## How It Works

1. **Server** stores peer info in DHT → gets back a hash
2. **You** manually share the hash (out-of-band)
3. **Client** uses the hash to retrieve the peer info from DHT
4. **Connection** happens!

This proves the DHT storage/retrieval works. The hash is just a workaround until we implement proper mutable storage with custom keys.
