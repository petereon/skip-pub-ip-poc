"""
Simple P2P Client - Uses Rust node for P2P, sends/receives messages via stdin/stdout
"""

import asyncio
import sys
from python.message_pb2 import Message


class P2PClient:
    """Client that sends and receives protobuf messages via P2P"""

    def __init__(self):
        self.rust_process = None
        self.server_peer_id = None

    async def start(self):
        """Start the Rust P2P node as subprocess"""
        print("🚀 Starting P2P Client...")

        # Start Rust node in client mode
        self.rust_process = await asyncio.create_subprocess_exec(
            "cargo",
            "run",
            "--bin",
            "p2p-node",
            "--",
            "--mode",
            "client",
            "--service",
            "myapi:v1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        print("✅ Rust P2P node started")
        print("🔍 Looking up server in DHT...\n")

        # Spawn read task
        asyncio.create_task(self.read_rust_output())

        # Wait a bit for connection
        await asyncio.sleep(3)

    async def read_rust_output(self):
        """Read messages from Rust node"""
        while True:
            line = await self.rust_process.stdout.readline()
            if not line:
                break

            output = line.decode().strip()
            print(f"[Rust] {output}")

            # Extract server peer ID if found
            if "Found service provider:" in output:
                parts = output.split("Found service provider:")
                if len(parts) > 1:
                    self.server_peer_id = parts[1].strip()
                    print(f"\n✅ Server found: {self.server_peer_id}\n")

    async def send_message(self, message: Message):
        """Send a message to the server"""
        if not self.server_peer_id:
            print("❌ Server not found yet, waiting...")
            await asyncio.sleep(2)
            if not self.server_peer_id:
                print("❌ Server not available")
                return

        cmd = f"send {self.server_peer_id} {message.to_json().decode()}\n"
        self.rust_process.stdin.write(cmd.encode())
        await self.rust_process.stdin.drain()
        print(f"📤 Sent: {message.type} - {message.payload.decode()}")

    async def listen(self):
        """Listen for incoming messages from server"""
        # Messages come through stdout from Rust node
        pass


async def interactive_mode(client: P2PClient):
    """Interactive mode for sending messages"""
    print("\n" + "=" * 60)
    print("🎮 Interactive Mode")
    print("=" * 60)
    print("\nCommands:")
    print("  <message>  - Send message to server")
    print("  quit       - Exit\n")

    while True:
        try:
            user_input = input("📝 Message: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                break

            # Create and send message
            msg = Message.create(
                msg_type="request",
                payload=user_input,
                metadata={"from": "python_client"},
            )

            await client.send_message(msg)

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            break


async def main():
    client = P2PClient()
    await client.start()

    try:
        await interactive_mode(client)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
