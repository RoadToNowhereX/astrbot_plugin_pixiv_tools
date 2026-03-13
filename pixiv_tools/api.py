"""
Pixiv API 管理模块
管理 AppPixivAPI 实例的创建和认证，支持定期自动刷新 Token
"""

import asyncio
from typing import Optional

from pixivpy3 import AppPixivAPI, PixivError
from astrbot.api import logger


class PixivApiManager:
    """Pixiv API 管理器，从插件配置读取 refresh_token，并支持定期自动刷新"""

    def __init__(self, refresh_token: str, refresh_interval: int = 60):
        """
        Args:
            refresh_token: Pixiv Refresh Token
            refresh_interval: 自动刷新间隔（分钟），设为 0 则禁用自动刷新
        """
        self._refresh_token = refresh_token
        self._refresh_interval = refresh_interval
        self._api: Optional[AppPixivAPI] = None
        self._refresh_task: Optional[asyncio.Task] = None

    def get_api(self) -> AppPixivAPI:
        """获取或创建已认证的 API 实例"""
        if self._api is None:
            if not self._refresh_token:
                raise ValueError(
                    "未配置 Pixiv Refresh Token，请在插件设置中填写。"
                )
            self._api = AppPixivAPI()
            self._api.auth(refresh_token=self._refresh_token)
            logger.info("Pixiv API 认证成功。")
        return self._api

    async def periodic_token_refresh(self):
        """定期尝试使用 refresh_token 进行认证以保持其活性"""
        while True:
            try:
                wait_seconds = self._refresh_interval * 60
                logger.debug(
                    f"Pixiv Token 刷新任务：等待 {self._refresh_interval} 分钟 ({wait_seconds} 秒)..."
                )
                await asyncio.sleep(wait_seconds)

                if not self._refresh_token:
                    logger.warning(
                        "Pixiv Token 刷新任务：未配置 Refresh Token，跳过本次刷新。"
                    )
                    continue

                # 确保 API 实例已存在，若未初始化则自动创建并认证
                if self._api is None:
                    logger.info(
                        "Pixiv Token 刷新任务：API 实例尚未初始化，尝试创建并认证..."
                    )
                    try:
                        self.get_api()
                        logger.info("Pixiv Token 刷新任务：API 实例初始化并认证成功。")
                    except Exception as init_e:
                        logger.error(
                            f"Pixiv Token 刷新任务：API 实例初始化失败 - {type(init_e).__name__}: {init_e}"
                        )
                    continue

                logger.info("Pixiv Token 刷新任务：尝试使用 Refresh Token 进行认证...")
                try:
                    self._api.auth(refresh_token=self._refresh_token)
                    logger.info("Pixiv Token 刷新任务：认证调用成功。")

                except PixivError as pe:
                    logger.error(
                        f"Pixiv Token 刷新任务：认证时发生 Pixiv API 错误 - {pe}"
                    )
                except Exception as e:
                    logger.error(
                        f"Pixiv Token 刷新任务：认证时发生未知错误 - {type(e).__name__}: {e}"
                    )
                    import traceback
                    logger.error(traceback.format_exc())

            except asyncio.CancelledError:
                logger.info("Pixiv Token 刷新任务：任务被取消，停止刷新。")
                break
            except Exception as loop_e:
                logger.error(
                    f"Pixiv Token 刷新任务：循环中发生意外错误 - {loop_e}，将在下次间隔后重试。"
                )
                import traceback
                logger.error(traceback.format_exc())

    def start_refresh_task(self) -> Optional[asyncio.Task]:
        """启动后台刷新任务并返回任务句柄（若已启动则复用原任务）。"""
        if self._refresh_interval <= 0:
            logger.info("Pixiv Tools 插件：Refresh Token 自动刷新已禁用。")
            return None

        if self._refresh_task and not self._refresh_task.done():
            return self._refresh_task

        self._refresh_task = asyncio.create_task(self.periodic_token_refresh())
        logger.info(
            f"Pixiv Tools 插件：已启动 Refresh Token 自动刷新任务，间隔 {self._refresh_interval} 分钟。"
        )
        return self._refresh_task

    async def stop_refresh_task(self) -> None:
        """停止后台刷新任务。"""
        if not self._refresh_task or self._refresh_task.done():
            return

        self._refresh_task.cancel()
        try:
            await self._refresh_task
        except asyncio.CancelledError:
            logger.info("Pixiv Token 刷新任务已成功取消。")
        except Exception as e:
            logger.error(f"等待 Pixiv Token 刷新任务取消时发生错误: {e}")
