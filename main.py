from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from async_rcon import AsyncRcon
from astrbot.api import AstrBotConfig  # 用来标识类型

@register("mcwl", "卡带酱", "MC 白名单插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        # 从配置里拿管理员 QQ 列表
        self.admin_qqs = set(self.config.get("admin_qqs", []))
        self.rcon_host = self.config.get("rcon_host")
        self.rcon_port = self.config.get("rcon_port")
        self.rcon_password = self.config.get("rcon_password")

    async def initialize(self):
        logger.info("mcwl plugin by kdj")

    async def add_whitelist_async(self, mcname: str) -> str:
        rcon = AsyncRcon(self.rcon_host, self.rcon_port, self.rcon_password)
        await rcon.connect()
        try:
            # 你之前用的是 swl add，如果服务器命令是 whitelist add，按实际改
            resp = await rcon.send_cmd(f"whitelist add {mcname}")
            return resp
        finally:
            await rcon.close()

    @filter.command("mcwl", desc="设置 MC 服务器白名单", alias={"mcwhitelist"})
    async def mcwl(self, event: AstrMessageEvent, mcname: str):
        user_name = event.get_sender_name()
        sender_qq = event.get_sender_id()

        if str(sender_qq) not in self.admin_qqs:
            yield event.plain_result(f"你好, {user_name}, 您没有权限执行此操作 :(")
            return

        try:
            resp = await self.add_whitelist_async(mcname)
            logger.info(f"RCON 执行结果: {resp}")
            yield event.plain_result(f"你好, {user_name}, 已尝试白名单添加 {mcname}，服务器返回：{resp}")
        except Exception as e:
            logger.error(f"RCON 执行失败: {e}")
            yield event.plain_result(f"你好, {user_name}, 添加白名单失败了：{e}")

    async def terminate(self):
        logger.info("mcwl plugin stopped")
