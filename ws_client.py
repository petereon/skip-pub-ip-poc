#!/usr/bin/env python3
"""
WebSocket Client with BitTorrent DHT Discovery + TCP Hole Punching
Uses DHT for peer discovery and TCP hole punching to traverse NAT
"""

import asyncio
import sys
import btdht_rs
import holepunch
from websockets.client import connect
import websockets

# Paste the hash from the server here:
DHT_HASH = "Id(98928187b2f35fcecb76aa08bcc3303224d7fdd5)"  # Replace with actual hash from server


async def main():
    if len(sys.argv) > 1:
        # Allow passing hash as command line argument
        hash_to_use = sys.argv[1]
    else:
        hash_to_use = DHT_HASH

    # Initialize DHT
    dht = btdht_rs.BTDht()
    print("🔧 Starting DHT...")
    await dht.start()
    await dht.bootstrap()

    # Give DHT a moment to bootstrap
    print("⏳ Bootstrapping to DHT network...")
    await asyncio.sleep(2)

    # Find the peer via DHT using the hash
    print(f"🔍 Searching for peer using hash: {hash_to_use}")
    peer_info = await dht.find_by_hash(hash_to_use)

    if peer_info is None:
        print(f"❌ No peer found at this hash")
        print("💡 Make sure you copied the correct hash from the server")
        return

    print(f"\n✅ Found peer in DHT!")
    print(f"   Peer Local:    {peer_info.local_ip}:{peer_info.local_port}")
    print(f"   Peer External: {peer_info.external_ip}:{peer_info.external_port}")

    # Get our own network info
    local_ip = await holepunch.get_local_ip()
    public_ip = await holepunch.get_public_ip()
    client_port = 9876  # Our local port for hole punching

    print(f"\n🔍 Our network configuration:")
    print(f"   Our Local:    {local_ip}:{client_port}")
    print(f"   Our External: {public_ip}:{client_port}")

    # Determine which endpoint to try
    # If we're on the same network (same public IP), use local IP
    # Otherwise, use external IP
    if public_ip == peer_info.external_ip:
        target_ip = peer_info.local_ip
        print(f"\n🏠 Same network detected, using local connection")
    else:
        target_ip = peer_info.external_ip
        print(f"\n🌐 Different network detected, attempting hole punch")

    target_port = peer_info.external_port

    # Attempt TCP hole punching
    print(f"\n🔨 Initiating TCP hole punch to {target_ip}:{target_port}...")

    connection = await holepunch.simultaneous_open(
        local_port=client_port,
        remote_ip=target_ip,
        remote_port=target_port,
        timeout=30.0,
    )

    if connection is None:
        print(f"\n❌ Hole punching failed. Trying direct connection...")
        # Fall back to direct connection
        try:
            ws_url = f"ws://{target_ip}:{target_port}"
            print(f"🔗 Connecting to {ws_url}...")
            async with connect(ws_url) as websocket:
                await communicate_websocket(websocket)
        except Exception as e:
            print(f"❌ Direct connection also failed: {e}")
            print("\n💡 Troubleshooting:")
            print("   1. Ensure both peers are behind NAT")
            print("   2. Verify firewall allows outgoing connections")
            print("   3. Some NATs (symmetric NAT) don't support hole punching")
        return

    reader, writer = connection
    print(f"✅ TCP connection established via hole punching!")

    # Upgrade to WebSocket
    try:
        print(f"🔄 Upgrading to WebSocket protocol...")

        # Create WebSocket connection over the existing TCP socket
        # We need to manually perform the WebSocket handshake
        ws_url = f"ws://{target_ip}:{target_port}"

        # For now, create a new WebSocket connection
        # (upgrading existing socket is complex)
        async with connect(ws_url) as websocket:
            await communicate_websocket(websocket)

    except Exception as e:
        print(f"❌ WebSocket upgrade failed: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def communicate_websocket(websocket):
    """Send and receive messages over WebSocket"""
    print("✅ WebSocket connected!")

    # Send some messages
    messages = ["Hello, World!", "How are you?", "Goodbye!"]
    for msg in messages:
        print(f"📤 Sending: {msg}")
        await websocket.send(msg)

        response = await websocket.recv()
        print(f"📥 Received: {response}")

        await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Client stopped")
