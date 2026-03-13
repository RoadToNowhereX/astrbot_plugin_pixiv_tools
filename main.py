from typing import Dict, Any

from astrbot.api.star import Context, Star
from astrbot.api import logger

from .pixiv_tools.api import PixivApiManager
from .pixiv_tools.llm_tools import create_pixiv_novel_tools


class PixivToolsPlugin(Star):
    """
    AstrBot 插件，提供 Pixiv 小说搜索、推荐、格式化等 LLM 工具。
    配置通过 AstrBot WebUI 进行管理。
    """

    def __init__(self, context: Context, config: Dict[str, Any]):
        super().__init__(context)
        self.config = config
        self.api_manager = None
        self.llm_tools = []

    async def initialize(self):
        """异步初始化：读取配置、创建 API 管理器、注册 LLM 工具"""
        refresh_token = self.config.get("refresh_token", "")
        if not refresh_token:
            logger.warning(
                "Pixiv Tools 插件：refresh_token 未配置，请在插件设置中填写。"
            )
            return

        # 读取刷新间隔配置
        refresh_interval = self.config.get("refresh_token_interval_minutes", 60)

        # 初始化 API 管理器
        self.api_manager = PixivApiManager(refresh_token, refresh_interval)

        # 启动后台 Token 自动刷新任务
        self.api_manager.start_refresh_task()

        # 创建并注册 LLM 工具
        self.llm_tools = create_pixiv_novel_tools(self.api_manager)
        try:
            self.context.add_llm_tools(*self.llm_tools)
            logger.info(
                f"Pixiv Tools 插件：已注册 {len(self.llm_tools)} 个 LLM 工具。"
            )
        except Exception as e:
            logger.error(f"Pixiv Tools 插件：注册 LLM 工具失败 - {e}")

    async def terminate(self):
        """插件停用时的清理"""
        # 停止后台刷新任务
        if self.api_manager:
            await self.api_manager.stop_refresh_task()
        logger.info("Pixiv Tools 插件已停用。")
