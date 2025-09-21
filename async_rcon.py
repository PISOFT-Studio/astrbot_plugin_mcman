# async_rcon.py
import asyncio
import struct

class AsyncRcon:
    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        # 登录
        await self._send_packet(0, 3, self.password)
        await self._recv_packet()

    async def send_cmd(self, command: str) -> str:
        await self._send_packet(1, 2, command)
        _, _, body = await self._recv_packet()
        return body

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def _send_packet(self, req_id: int, ptype: int, payload: str):
        data = struct.pack("<ii", req_id, ptype) + payload.encode() + b"\x00\x00"
        length = struct.pack("<i", len(data))
        self.writer.write(length + data)
        await self.writer.drain()

    async def _recv_packet(self):
        length_bytes = await self.reader.readexactly(4)
        length = struct.unpack("<i", length_bytes)[0]
        data = await self.reader.readexactly(length)
        req_id, ptype = struct.unpack("<ii", data[:8])
        body = data[8:-2].decode(errors="ignore")
        return req_id, ptype, body
