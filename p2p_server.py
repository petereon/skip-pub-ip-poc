"""
Simple P2P Server - Uses Rust node for P2P, handles messages via stdin/stdout
"""

import asyncio
import json
import sys


class P2PServer:
    """Server that sends and receives protobuf messages via P2P"""

    def __init__(self):
        self.rust_process = None

    async def start(self):
        """Start the Rust P2P node as subprocess"""
        print("🚀 Starting P2P Server...")

        # Start Rust node in server mode
        self.rust_process = await asyncio.create_subprocess_exec(
            "cargo",
            "run",
            "--bin",
            "p2p-node",
            "--",
            "--mode",
            "server",
            "--service",
            "myapi:v1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        print("✅ Rust P2P node started")

        # Spawn tasks
        asyncio.create_task(self.read_rust_output())
        asyncio.create_task(self.handle_messages())

    async def read_rust_output(self):
        """Read messages from Rust node"""
        while True:
            line = await self.rust_process.stdout.readline()
            if not line:
                break
            print(f"[Rust] {line.decode().strip()}")

    async def handle_messages(self):
        """Handle incoming messages from clients"""
        print("\n📨 Server ready to receive messages...")
        print("💡 Try running client to send messages\n")

        # For demo, just keep alive
        while True:
            await asyncio.sleep(1)

    async def send_message(self, peer_id: str, message: dict):
        """Send a JSON message to a peer"""
        cmd = f"send {peer_id} {json.dumps(message)}\n"
        self.rust_process.stdin.write(cmd.encode())
        await self.rust_process.stdin.drain()
        print(f"📤 Sent to {peer_id}: {message.get('type', 'unknown')}")

    async def listen(self):
        """Listen for incoming messages"""
        # Messages come through stdin from Rust node
        # In practice, we'd parse these and handle them
        pass


async def main():
    server = P2PServer()
    await server.start()

    try:
        # Keep running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
