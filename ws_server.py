#!/usr/bin/env python3
"""
WebSocket Server with BitTorrent DHT Registration + TCP Hole Punching
Uses DHT for peer discovery and TCP hole punching for NAT traversal
"""

import asyncio
import btdht_rs
from websockets.server import serve
import holepunch

SERVICE_KEY = "my-websocket-service"
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

    # Give DHT time to bootstrap
    print("⏳ Bootstrapping to DHT network...")
    await asyncio.sleep(2)

    # Discover network configuration
    print("🔍 Discovering network configuration...")
    local_ip = await holepunch.get_local_ip()
    public_ip = await holepunch.get_public_ip()

    print(f"   Local IP:  {local_ip}:{WS_PORT}")
    print(f"   Public IP: {public_ip}:{WS_PORT}")

    # Register both endpoints to DHT
    print(f"\n📢 Registering service '{SERVICE_KEY}' to BitTorrent DHT...")
    hash_str = await dht.register_service(
        SERVICE_KEY, local_ip, WS_PORT, public_ip, WS_PORT
    )

    print(f"\n{'=' * 60}")
    print(f"📋 COPY THIS HASH FOR THE CLIENT:")
    print(f"   {hash_str}")
    print(f"{'=' * 60}\n")

    print(f"🚀 WebSocket server starting on 0.0.0.0:{WS_PORT}")
    print(f"🔓 Ready for hole-punching connections")
    print(f"💡 Clients will use TCP hole punching to connect\n")

    async with serve(handler, "0.0.0.0", WS_PORT, reuse_address=True, reuse_port=True):
        # Keep the server running
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
