#!/usr/bin/env python3
"""
WebSocket Client with BitTorrent DHT Discovery
Discovers the server via DHT using the hash from the server
"""

import asyncio
import sys
import btdht_rs
from websockets.client import connect

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
    await asyncio.sleep(2)

    # Find the WebSocket server via DHT using the hash
    print(f"🔍 Searching for service using hash: {hash_to_use}")
    ws_url = await dht.find_by_hash(hash_to_use)

    if ws_url is None:
        print(f"❌ No service found at this hash")
        print("💡 Make sure you copied the correct hash from the server")
        return

    print(f"✅ Found server at: {ws_url}")

    # Connect to the WebSocket server
    try:
        print(f"🔗 Connecting to {ws_url}...")
        async with connect(ws_url) as websocket:
            print("✅ Connected!")

            # Send some messages
            messages = ["Hello, World!", "How are you?", "Goodbye!"]
            for msg in messages:
                print(f"📤 Sending: {msg}")
                await websocket.send(msg)

                response = await websocket.recv()
                print(f"📥 Received: {response}")

                await asyncio.sleep(1)

    except Exception as e:
        print(f"❌ Connection failed: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Client stopped")
