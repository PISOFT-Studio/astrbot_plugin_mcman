import asyncio
import struct
import re
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig  # 配置管理


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


def strip_mc_color(text: str) -> str:
    return re.sub(r"§.", "", text)


async def rcon_whitelist(host, port, password, o: str, mcname: str = "") -> str:
    """异步执行 RCON 命令"""
    rcon = AsyncRcon(host, port, password)
    await rcon.connect()
    try:
        if mcname:
            resp = await rcon.send_cmd(f"swl {o} {mcname}")
        else:
            resp = await rcon.send_cmd(f"swl {o}")
        return resp
    finally:
        await rcon.close()


async def rcon_ban(host, port, password, mcname: str = "") -> str:
    """异步执行 RCON 命令"""
    rcon = AsyncRcon(host, port, password)
    await rcon.connect()
    try:
        if mcname:
            resp = await rcon.send_cmd(f"ban {mcname}")
        else:
            resp = await rcon.send_cmd(f"ban")
        return resp
    finally:
        await rcon.close()


async def rcon_unban(host, port, password, mcname: str = "") -> str:
    """异步执行 RCON 命令"""
    rcon = AsyncRcon(host, port, password)
    await rcon.connect()
    try:
        if mcname:
            resp = await rcon.send_cmd(f"pardon {mcname}")
        else:
            resp = await rcon.send_cmd(f"pardon")
        return resp
    finally:
        await rcon.close()


async def rcon_kick(host, port, password, mcname: str = "", reason: str = "") -> str:
    """异步执行 RCON 命令"""
    rcon = AsyncRcon(host, port, password)
    await rcon.connect()
    try:
        if mcname:
            resp = await rcon.send_cmd(f"kick {mcname} {reason}")
        else:
            resp = await rcon.send_cmd(f"kick")
        return resp
    finally:
        await rcon.close()


async def rcon_banlist(host, port, password) -> str:
    """异步执行 RCON 命令"""
    rcon = AsyncRcon(host, port, password)
    await rcon.connect()
    try:
        resp = await rcon.send_cmd(f"banlist")
        return resp
    finally:
        await rcon.close()


async def rcon_list(host, port, password) -> str:
    """异步执行 RCON 命令"""
    rcon = AsyncRcon(host, port, password)
    await rcon.connect()
    try:
        resp = await rcon.send_cmd(f"list")
        return resp
    finally:
        await rcon.close()


async def rcon_tempban(host, port, password, mcname: str, time: str, reason: str) -> str:
    """异步执行 RCON 命令"""
    rcon = AsyncRcon(host, port, password)
    await rcon.connect()
    try:
        if mcname:
            if time:
                if reason:
                    resp = await rcon.send_cmd(f"tempban {mcname} {time} {reason}")
                else:
                    resp = await rcon.send_cmd(f"tempban {mcname} {time}")
            else:
                resp = await rcon.send_cmd(f"tempban {mcname}")
        else:
            resp = await rcon.send_cmd(f"tempban")
        return resp
    finally:
        await rcon.close()


@register("MC管理器", "卡带酱", "一个基于RCON协议的MC服务器管理器插件", "1.0.2")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        # 管理员 QQ
        self.admin_qqs = set(self.config.get("admin_qqs", []))
        # RCON 配置
        self.rcon_host = self.config.get("rcon_host")
        self.rcon_port = self.config.get("rcon_port")
        self.rcon_password = self.config.get("rcon_password")

    async def initialize(self):
        logger.info("mcman plugin by kdj")

    @filter.command("mcwl", desc="MC 白名单管理 (list/add/remove)", alias={"mcwhitelist"})
    async def mcwl(self, event: AstrMessageEvent, o: str, mcname: str = ""):
        """MC 白名单管理命令"""
        user_name = event.get_sender_name()
        sender_qq = event.get_sender_id()
        named = f"{user_name}({sender_qq})"

        # 权限检查
        if str(sender_qq) not in self.admin_qqs:
            yield event.plain_result(f"你好, {named}, 您没有权限执行此操作 :(")
            return

        # 参数校验
        if o not in ("list", "add", "remove"):
            yield event.plain_result(
                f"你好, {named}, 不支持的操作 `{o}`，可选: list, add, remove"
            )
            return

        try:
            resp = await rcon_whitelist(self.rcon_host, self.rcon_port, self.rcon_password, o, mcname)
            cresp = strip_mc_color(resp)
            logger.info(f"RCON 执行结果: {resp}")
            yield event.plain_result(
                f"你好, {named}, 已尝试执行 `whitelist {o} {mcname}`\n\n服务器返回：\n{cresp}"
            )
        except Exception as e:
            logger.error(f"RCON 执行失败: {e}")
            yield event.plain_result(f"你好, {named}, 操作失败：{e}")

    @filter.command("mcban", desc="MC 黑名单添加")
    async def mcban(self, event: AstrMessageEvent, mcname: str = ""):
        """MC 黑名单添加命令"""
        user_name = event.get_sender_name()
        sender_qq = event.get_sender_id()
        named = f"{user_name}({sender_qq})"

        # 权限检查
        if str(sender_qq) not in self.admin_qqs:
            yield event.plain_result(f"你好, {named}, 您没有权限执行此操作 :(")
            return

        try:
            resp = await rcon_ban(self.rcon_host, self.rcon_port, self.rcon_password, mcname)
            cresp = strip_mc_color(resp)
            logger.info(f"RCON 执行结果: {resp}")
            yield event.plain_result(
                f"你好, {named}, 已尝试执行 `ban {mcname}`\n\n服务器返回：\n{cresp}"
            )
        except Exception as e:
            logger.error(f"RCON 执行失败: {e}")
            yield event.plain_result(f"你好, {named}, 操作失败：{e}")

    @filter.command("mcpardon", desc="MC 黑名单移除", alias={"mcunban"})
    async def mcpardon(self, event: AstrMessageEvent, mcname: str = ""):
        """MC 黑名单移除命令"""
        user_name = event.get_sender_name()
        sender_qq = event.get_sender_id()
        named = f"{user_name}({sender_qq})"

        # 权限检查
        if str(sender_qq) not in self.admin_qqs:
            yield event.plain_result(f"你好, {named}, 您没有权限执行此操作 :(")
            return

        try:
            resp = await rcon_unban(self.rcon_host, self.rcon_port, self.rcon_password, mcname)
            cresp = strip_mc_color(resp)
            logger.info(f"RCON 执行结果: {resp}")
            yield event.plain_result(
                f"你好, {named}, 已尝试执行 `pardon {mcname}`\n\n服务器返回：\n{cresp}"
            )
        except Exception as e:
            logger.error(f"RCON 执行失败: {e}")
            yield event.plain_result(f"你好, {named}, 操作失败：{e}")

    @filter.command("mcbanlist", desc="MC 黑名单查看", alias={"mcbl"})
    async def mcbl(self, event: AstrMessageEvent):
        """MC 黑名单查看命令"""
        user_name = event.get_sender_name()
        sender_qq = event.get_sender_id()
        named = f"{user_name}({sender_qq})"

        # # 权限检查
        # if str(sender_qq) not in self.admin_qqs:
        #     yield event.plain_result(f"你好, {named}, 您没有权限执行此操作 :(")
        #     return

        try:
            resp = await rcon_banlist(self.rcon_host, self.rcon_port, self.rcon_password)
            cresp = strip_mc_color(resp)
            logger.info(f"RCON 执行结果: {resp}")
            yield event.plain_result(
                f"你好, {named}, 已尝试执行 `banlist`\n\n服务器返回：\n{cresp}"
            )
        except Exception as e:
            logger.error(f"RCON 执行失败: {e}")
            yield event.plain_result(f"你好, {named}, 操作失败：{e}")

    @filter.command("mclist", desc="MC 查看在线玩家", alias={"mcl"})
    async def mclist(self, event: AstrMessageEvent):
        """MC 查看在线玩家命令"""
        user_name = event.get_sender_name()
        sender_qq = event.get_sender_id()
        named = f"{user_name}({sender_qq})"

        # # 权限检查
        # if str(sender_qq) not in self.admin_qqs:
        #     yield event.plain_result(f"你好, {named}, 您没有权限执行此操作 :(")
        #     return

        try:
            resp = await rcon_list(self.rcon_host, self.rcon_port, self.rcon_password)
            cresp = strip_mc_color(resp)
            logger.info(f"RCON 执行结果: {resp}")
            yield event.plain_result(
                f"你好, {named}, 已尝试执行 `list`\n\n服务器返回：\n{cresp}"
            )
        except Exception as e:
            logger.error(f"RCON 执行失败: {e}")
            yield event.plain_result(f"你好, {named}, 操作失败：{e}")

    @filter.command("mckick", desc="MC 踢出指定玩家", alias={"mck"})
    async def mckick(self, event: AstrMessageEvent, mcname: str = "", reason: str = ""):
        """MC 踢出指定玩家命令"""
        user_name = event.get_sender_name()
        sender_qq = event.get_sender_id()
        named = f"{user_name}({sender_qq})"

        # 权限检查
        if str(sender_qq) not in self.admin_qqs:
            yield event.plain_result(f"你好, {named}, 您没有权限执行此操作 :(")
            return

        try:
            resp = await rcon_kick(self.rcon_host, self.rcon_port, self.rcon_password, mcname, reason)
            cresp = strip_mc_color(resp)
            logger.info(f"RCON 执行结果: {resp}")
            yield event.plain_result(
                f"你好, {named}, 已尝试执行 `kick {mcname} {reason}`\n\n服务器返回：\n{cresp}"
            )
        except Exception as e:
            logger.error(f"RCON 执行失败: {e}")
            yield event.plain_result(f"你好, {named}, 操作失败：{e}")

    @filter.command("mctempban", desc="MC 临时黑名单", alias={"mctb"})
    async def mctempban(self, event: AstrMessageEvent, mcname: str = "", time: str = "", reason: str = ""):
        """MC 临时黑名单命令"""
        user_name = event.get_sender_name()
        sender_qq = event.get_sender_id()
        named = f"{user_name}({sender_qq})"

        # 权限检查
        if str(sender_qq) not in self.admin_qqs:
            yield event.plain_result(f"你好, {named}, 您没有权限执行此操作 :(")
            return

        try:
            resp = await rcon_tempban(self.rcon_host, self.rcon_port, self.rcon_password, mcname)
            cresp = strip_mc_color(resp)
            logger.info(f"RCON 执行结果: {resp}")
            yield event.plain_result(
                f"你好, {named}, 已尝试执行 `tempban {mcname} {time} {reason}`\n\n服务器返回：\n{cresp}"
            )
        except Exception as e:
            logger.error(f"RCON 执行失败: {e}")
            yield event.plain_result(f"你好, {named}, 操作失败：{e}")

    async def terminate(self):
        logger.info("mcman plugin stopped")
