#!/usr/bin/env python3
"""
WebSocket Server with BitTorrent DHT Registration
Registers itself to the DHT so clients can discover it
"""

import asyncio
import btdht_rs
from websockets.server import serve

SERVICE_KEY = "my-websocket-service"  # This is what clients will search for
WS_PORT = 8765


async def handler(websocket):
    """Handle WebSocket connections"""
    print(f"✅ Client connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            print(f"📨 Received: {message}")
            # Echo back the message
            await websocket.send(f"Echo: {message}")
    except Exception as e:
        print(f"❌ Connection error: {e}")
    finally:
        print(f"👋 Client disconnected: {websocket.remote_address}")


async def main():
    # Initialize DHT
    dht = btdht_rs.BTDht()
    print("🔧 Starting DHT...")
    await dht.start()
    await dht.bootstrap()

    # Register this WebSocket server to the DHT
    # Note: Use your actual public IP or hostname here
    # For local testing, you can use localhost
    ws_url = f"ws://localhost:{WS_PORT}"

    print(f"📢 Registering service '{SERVICE_KEY}' -> {ws_url} to BitTorrent DHT...")
    hash_str = await dht.register_service(SERVICE_KEY, ws_url, WS_PORT)

    print(f"\n{'=' * 60}")
    print(f"📋 COPY THIS HASH FOR THE CLIENT:")
    print(f"   {hash_str}")
    print(f"{'=' * 60}\n")

    # Start WebSocket server
    print(f"🚀 WebSocket server started on {ws_url}")
    print(f"💡 Clients can find this server using service key: '{SERVICE_KEY}'")

    async with serve(handler, "0.0.0.0", WS_PORT):
        # Keep the server running
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
