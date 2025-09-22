import asyncio
import json
import struct
import re
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig  # 配置管理


class AsyncRcon:  # 异步RCON类
    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        await self._send_packet(0, 3, self.password)  # 登录
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
        body = data[8:].rstrip(b"\x00").decode(errors="ignore")
        return req_id, ptype, body


def strip_mc_color(text: str) -> str:
    return re.sub(r"§.", "", text)


async def rcon_command(
    host: str, port: int, password: str, command: str
) -> str:  # 执行rcon命令
    """统一执行任意 RCON 命令"""
    rcon = AsyncRcon(host, port, password)
    await rcon.connect()
    try:
        return await rcon.send_cmd(command)
    finally:
        await rcon.close()


@register(
    "astrbot_plugin_mcman", "卡带酱", "一个基于RCON协议的MC服务器管理器插件", "1.1.0"
)
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.whitelist_command = self.config.get("whitelist_command", "whitelist")
        self.admin_qqs = set(self.config.get("admin_qqs", []))
        self.rcon_host = self.config.get("rcon_host")
        self.rcon_port = self.config.get("rcon_port")
        self.rcon_password = self.config.get("rcon_password")

    async def initialize(self):
        logger.info("mcman plugin by kdj")

    def is_admin(self, qqid: str) -> bool:
        return qqid in self.admin_qqs

    async def execute_and_reply(self, event: AstrMessageEvent, command: str, desc: str):
        """通用执行 + 回复逻辑"""
        user_name = event.get_sender_name()
        sender_qq = str(event.get_sender_id())
        named = f"{user_name}({sender_qq})"

        try:
            resp = await rcon_command(
                self.rcon_host, self.rcon_port, self.rcon_password, command
            )
            cresp = strip_mc_color(resp)
            logger.info(f"RCON 执行结果: {resp}")
            yield event.plain_result(
                f"你好, {named}, 已尝试执行 `{command}` ({desc})\n\n服务器返回：\n{cresp}"
            )
        except Exception as e:
            logger.error(f"RCON 执行失败: {e}")
            yield event.plain_result(f"你好, {named}, 操作失败：{e}")

    @filter.command("mcwl", desc="MC 白名单管理", alias={"mcwhitelist"})
    async def mcwl(self, event: AstrMessageEvent, o: str, mcname: str = ""):
        if not self.is_admin(str(event.get_sender_id())):
            yield event.plain_result("抱歉，你没有权限执行此操作。")
            return
        command = f"{self.whitelist_command} {o} {mcname}".strip()
        async for msg in self.execute_and_reply(event, command, "白名单管理"):
            yield msg

    @filter.command("mcban", desc="MC 黑名单添加")
    async def mcban(self, event: AstrMessageEvent, mcname: str = "", reason: str = ""):
        if not self.is_admin(str(event.get_sender_id())):
            yield event.plain_result("抱歉，你没有权限执行此操作。")
            return
        command = f"ban {mcname} {reason}".strip()
        async for msg in self.execute_and_reply(event, command, "黑名单添加"):
            yield msg

    @filter.command("mcpardon", desc="MC 黑名单移除", alias={"mcunban"})
    async def mcpardon(self, event: AstrMessageEvent, mcname: str = ""):
        if not self.is_admin(str(event.get_sender_id())):
            yield event.plain_result("抱歉，你没有权限执行此操作。")
            return
        command = f"pardon {mcname}".strip()
        async for msg in self.execute_and_reply(event, command, "黑名单移除"):
            yield msg

    @filter.command("mcbanlist", desc="MC 黑名单查看", alias={"mcbl"})
    async def mcbl(self, event: AstrMessageEvent):
        async for msg in self.execute_and_reply(event, "banlist", "查看黑名单"):
            yield msg

    @filter.command("mclist", desc="MC 查看在线玩家", alias={"mcl"})
    async def mclist(self, event: AstrMessageEvent):
        async for msg in self.execute_and_reply(event, "list", "查看在线玩家"):
            yield msg

    @filter.command("mckick", desc="MC 踢出指定玩家", alias={"mck"})
    async def mckick(self, event: AstrMessageEvent, mcname: str = "", reason: str = ""):
        if not self.is_admin(str(event.get_sender_id())):
            yield event.plain_result("抱歉，你没有权限执行此操作。")
            return
        command = f"kick {mcname} {reason}".strip()
        async for msg in self.execute_and_reply(event, command, "踢出玩家"):
            yield msg

    @filter.command("mctempban", desc="MC 临时黑名单", alias={"mctb"})
    async def mctempban(
        self,
        event: AstrMessageEvent,
        mcname: str = "",
        time: str = "",
        reason: str = "",
    ):
        if not self.is_admin(str(event.get_sender_id())):
            yield event.plain_result("抱歉，你没有权限执行此操作。")
            return
        command = f"tempban {mcname} {time} {reason}".strip()
        async for msg in self.execute_and_reply(event, command, "临时封禁"):
            yield msg

    @filter.command("mcsay", desc="MC 说话", alias={"mcs"})
    async def mcsay(self, event: AstrMessageEvent, text: str = ""):
        user_name = event.get_sender_name()
        sender_qq = str(event.get_sender_id())
        named = f"{user_name}({sender_qq})"

        if not text:
            yield event.plain_result(f"你好, {named}, 请输入信息!")
            return

        message = [
            {"text": f"(QQ消息) ", "color": "aqua"},
            {"text": f"<{named}>", "color": "green", "underlined": True},
            {"text": " 说: ", "color": "white"},
            {"text": text, "color": "yellow"},
        ]
        command = f"tellraw @a {json.dumps(message, ensure_ascii=False)}"
        async for msg in self.execute_and_reply(event, command, "玩家发言"):
            yield msg

    @filter.command("mcbroadcast", desc="MC 广播消息", alias={"mcb", "mcbc"})
    async def mcbroadcast(self, event: AstrMessageEvent, text: str = ""):
        user_name = event.get_sender_name()
        sender_qq = str(event.get_sender_id())
        named = f"{user_name}({sender_qq})"
        if not self.is_admin(str(event.get_sender_id())):
            yield event.plain_result("抱歉，你没有权限执行此操作。")
            return
        if not text:
            yield event.plain_result(f"你好, {named}, 请输入广播信息!")
            return

        message = [
            {"text": f"<管理员广播消息>", "color": "green", "underlined": True},
            {"text": " ", "color": "white"},
            {"text": text, "color": "yellow"},
        ]
        command = f"tellraw @a {json.dumps(message, ensure_ascii=False)}"
        async for msg in self.execute_and_reply(event, command, "广播消息"):
            yield msg

    async def terminate(self):
        logger.info("mcman plugin stopped")
