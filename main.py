from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from mcrcon import MCRcon
import asyncio


async def add_whitelist_async(mc_host, mc_port, rcon_pwd, mcname: str):
    def _do_rcon():
        with MCRcon(mc_host, rcon_pwd, port=mc_port) as mcr:
            resp = mcr.command(f"swl add {mcname}")
            return resp

    # 把同步的 rcon 调用放到线程池里跑
    return await asyncio.to_thread(_do_rcon)


@register("mcwl", "卡带酱", "mcwl", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        logger.info("mcwl plugin by kdj")

    @filter.command("mcwl", desc="设置MC服务器白名单", alias={"mcwhitelist"})
    async def mcwl(self, event: AstrMessageEvent, mcname: str):
        """mcwl"""
        user_name = event.get_sender_name()
        sender_qq = event.get_sender_id()

        if sender_qq not in ("2569507513", "1546840139"):
            yield event.plain_result(f"你好, {user_name}, 您似乎没有权限 :(")
            return

        # 执行 rcon 白名单添加
        try:
            resp = await add_whitelist_async("host", 25575, "password", mcname)
            logger.info(f"RCON执行结果: {resp}")
            yield event.plain_result(
                f"你好, {user_name}, 已尝试对白名单添加 {mcname}，服务器返回: {resp}"
            )
        except Exception as e:
            logger.error(f"RCON 执行失败: {e}")
            yield event.plain_result(f"你好, {user_name}, 添加白名单失败了: {e}")

    async def terminate(self):
        logger.info("mcwl plugin stopped")
