#!/usr/bin/env python3
"""
TCP Hole Punching Implementation
Mimics BitTorrent's NAT traversal technique
"""

import asyncio
import socket
import struct
from typing import Optional, Tuple


async def get_local_ip() -> str:
    """Get local IP address (not 127.0.0.1)"""
    try:
        # Create a UDP socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


async def get_public_ip() -> str:
    """Discover public IP using STUN-like technique"""
    import aiohttp

    services = [
        "https://api.ipify.org?format=text",
        "https://icanhazip.com",
        "https://ifconfig.me/ip",
    ]

    for service in services:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    service, timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return (await response.text()).strip()
        except Exception:
            continue

    return await get_local_ip()


async def tcp_hole_punch_listen(
    local_port: int, timeout: float = 30.0
) -> Optional[Tuple[asyncio.StreamReader, asyncio.StreamWriter]]:
    """
    Listen for incoming TCP connections with SO_REUSEADDR to allow simultaneous bind.
    This creates the "hole" in the NAT.
    """
    server = None
    connection_future = asyncio.Future()

    async def handle_client(reader, writer):
        if not connection_future.done():
            connection_future.set_result((reader, writer))

    try:
        # Create server with SO_REUSEADDR
        server = await asyncio.start_server(
            handle_client, "0.0.0.0", local_port, reuse_address=True, reuse_port=True
        )

        print(f"🔓 Listening on port {local_port} for hole punch...")

        # Wait for connection with timeout
        try:
            result = await asyncio.wait_for(connection_future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            print(f"⏱️  Listen timeout after {timeout}s")
            return None

    except Exception as e:
        print(f"❌ Listen error: {e}")
        return None
    finally:
        if server:
            server.close()
            await server.wait_closed()


async def tcp_hole_punch_connect(
    local_port: int,
    remote_ip: str,
    remote_port: int,
    delay: float = 0.5,
    max_attempts: int = 10,
) -> Optional[Tuple[asyncio.StreamReader, asyncio.StreamWriter]]:
    """
    Attempt to connect from a specific local port to remote endpoint.
    Uses SO_REUSEADDR to allow binding to the same port as the listener.
    This creates outgoing packets that "punch" through our NAT.
    """

    for attempt in range(max_attempts):
        try:
            # Wait a bit before each attempt
            await asyncio.sleep(delay)

            print(
                f"🔨 Punch attempt {attempt + 1}/{max_attempts}: {remote_ip}:{remote_port}"
            )

            # Create socket with reuse options
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Try to enable SO_REUSEPORT on platforms that support it
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass

            # Bind to specific local port (this is key for hole punching)
            sock.bind(("0.0.0.0", local_port))
            sock.setblocking(False)

            # Attempt connection
            try:
                await asyncio.wait_for(
                    asyncio.get_event_loop().sock_connect(
                        sock, (remote_ip, remote_port)
                    ),
                    timeout=2.0,
                )

                # Success! Convert to streams
                reader, writer = await asyncio.open_connection(sock=sock)
                print(f"✅ Hole punch successful!")
                return reader, writer

            except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                sock.close()
                if attempt < max_attempts - 1:
                    continue
                else:
                    print(f"❌ All connection attempts failed: {e}")
                    return None

        except Exception as e:
            print(f"❌ Punch attempt {attempt + 1} error: {e}")
            if attempt == max_attempts - 1:
                return None

    return None


async def simultaneous_open(
    local_port: int, remote_ip: str, remote_port: int, timeout: float = 30.0
) -> Optional[Tuple[asyncio.StreamReader, asyncio.StreamWriter]]:
    """
    Perform simultaneous TCP open - both sides try to connect to each other.
    This is the core of TCP hole punching.

    Returns the first successful connection (either incoming or outgoing).
    """

    print(f"\n🔀 Starting simultaneous open:")
    print(f"   Local port: {local_port}")
    print(f"   Remote: {remote_ip}:{remote_port}")

    # Start both listen and connect tasks
    listen_task = asyncio.create_task(tcp_hole_punch_listen(local_port, timeout))

    # Give listener a moment to start
    await asyncio.sleep(0.5)

    connect_task = asyncio.create_task(
        tcp_hole_punch_connect(local_port, remote_ip, remote_port)
    )

    # Wait for whichever succeeds first
    done, pending = await asyncio.wait(
        [listen_task, connect_task], return_when=asyncio.FIRST_COMPLETED
    )

    # Cancel the other task
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Return the successful connection
    for task in done:
        result = task.result()
        if result is not None:
            return result

    return None
