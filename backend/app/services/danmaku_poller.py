import asyncio
import threading
import time
from typing import Dict, Optional, Set
from yt_chat_downloader import YouTubeChatDownloader
from app.services.connection_manager import manager
from app.config import settings


class DanmakuPoller:
    """YouTube弹幕轮询器，为每个视频维护一个轮询任务"""

    def __init__(self):
        self.pollers: Dict[str, "VideoPoller"] = {}
        self.lock = threading.Lock()

    def start_polling(self, video_id: str):
        """启动指定视频的轮询任务"""
        with self.lock:
            if video_id in self.pollers:
                return  # 已经在运行

            poller = VideoPoller(video_id)
            self.pollers[video_id] = poller
            poller.start()

    def stop_polling(self, video_id: str):
        """停止指定视频的轮询任务"""
        with self.lock:
            if video_id in self.pollers:
                self.pollers[video_id].stop()
                del self.pollers[video_id]

    def get_active_videos(self) -> Set[str]:
        """获取当前正在轮询的视频ID列表"""
        with self.lock:
            return set(self.pollers.keys())


class VideoPoller:
    """单个视频的轮询器"""

    def __init__(self, video_id: str):
        self.video_id = video_id
        self.downloader = YouTubeChatDownloader()
        self.continuation: Optional[str] = None
        self.api_key: Optional[str] = None
        self.version: Optional[str] = None
        self.is_live_stream = False
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_message_ids: Set[str] = set()
        self._initialized = False

    def _initialize(self):
        """初始化：获取视频信息和continuation token"""
        if self._initialized:
            return

        try:
            video_info = self.downloader.get_video_info(self.video_id)
            self.is_live_stream = video_info.get("is_live", False)

            html = self.downloader.fetch_html(
                f"https://www.youtube.com/watch?v={self.video_id}"
            )
            self.api_key, self.version, yid = self.downloader.extract_innertube_params(
                html
            )

            if yid:
                self.continuation = self.downloader.find_continuation(yid)

            self._initialized = True
            print(
                f"Initialized poller for {self.video_id}: live={self.is_live_stream}, continuation={bool(self.continuation)}"
            )
        except Exception as e:
            print(f"Failed to initialize poller for {self.video_id}: {e}")

    def start(self):
        """启动轮询线程"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """停止轮询"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _poll_loop(self):
        """轮询循环"""
        self._initialize()

        if not self.continuation:
            # 尝试获取录播弹幕（一次性）
            self._fetch_replay_once()
            self.running = False
            return

        while self.running:
            try:
                messages = self._fetch_new_messages()
                if messages:
                    new_messages = self._filter_new_messages(messages)
                    if new_messages:
                        asyncio.run(self._send_messages(new_messages))

                time.sleep(1.0)  # 1秒轮询间隔
            except Exception as e:
                print(f"Polling error for {self.video_id}: {e}")
                time.sleep(5)

    def _fetch_new_messages(self):
        """获取新消息"""
        if not self.continuation or not self.api_key:
            return []

        try:
            chat_data = self.downloader.get_live_chat_data(
                self.api_key,
                self.version,
                self.continuation,
                is_live=self.is_live_stream,
            )

            messages, _ = self.downloader.parse_live_chat_messages(chat_data)

            # 额外解析 sticker 消息
            sticker_messages = self._parse_sticker_messages(chat_data)
            messages.extend(sticker_messages)

            # 更新continuation token
            next_cont = self.downloader.extract_next_continuation(chat_data)
            if next_cont:
                self.continuation = next_cont

            return messages
        except Exception as e:
            print(f"Error fetching messages: {e}")
            return []

    def _parse_sticker_messages(self, chat_data: dict) -> list:
        """解析 sticker 消息"""
        messages = []

        try:
            # 获取 actions
            actions = None
            if "actions" in chat_data:
                actions = chat_data["actions"]
            elif "continuationContents" in chat_data:
                actions = chat_data["continuationContents"]["liveChatContinuation"].get(
                    "actions", []
                )
            elif "contents" in chat_data:
                actions = chat_data["contents"]["liveChatRenderer"].get("actions", [])

            if not actions:
                return messages

            for action in actions:
                # 处理录播中的 sticker
                if "replayChatItemAction" in action:
                    replay_action = action["replayChatItemAction"]
                    video_offset = replay_action.get("videoOffsetTimeMsec", "0")
                    chat_actions = replay_action.get("actions", [])
                    if chat_actions and "addChatItemAction" in chat_actions[0]:
                        item = chat_actions[0]["addChatItemAction"]["item"]
                        sticker_msg = self._extract_sticker_from_item(
                            item, video_offset
                        )
                        if sticker_msg:
                            messages.append(sticker_msg)

                # 处理直播中的 sticker
                elif "addChatItemAction" in action:
                    item = action["addChatItemAction"]["item"]
                    video_offset = "0"
                    if "timestampUsec" in action.get("addChatItemAction", {}):
                        video_offset = str(
                            int(action["addChatItemAction"]["timestampUsec"]) // 1000
                        )
                    sticker_msg = self._extract_sticker_from_item(item, video_offset)
                    if sticker_msg:
                        messages.append(sticker_msg)

        except Exception as e:
            print(f"Error parsing sticker messages: {e}")

        return messages

    def _extract_sticker_from_item(
        self, item: dict, video_offset: str = "0"
    ) -> Optional[dict]:
        """从 item 中提取 sticker 信息"""
        try:
            if "liveChatStickerRenderer" not in item:
                return None

            renderer = item["liveChatStickerRenderer"]

            # 获取 sticker 图片 URL
            sticker = renderer.get("sticker", {})
            thumbnails = sticker.get("thumbnails", [])
            img_url = thumbnails[0].get("url", "") if thumbnails else ""

            if not img_url:
                return None

            # 获取 alt 文字
            accessibility = sticker.get("accessibility", {})
            alt_text = accessibility.get("accessibilityData", {}).get(
                "label", "Sticker"
            )

            # 获取作者信息
            author = renderer.get("authorName", {})
            author_name = author.get("simpleText", "").strip() if author else ""
            author_id = renderer.get("authorExternalChannelId", "")

            return {
                "user_id": author_id,
                "user_display_name": author_name,
                "user_handle": author_name,
                "datetime": "",
                "timestamp": "0:00",
                "comment": alt_text,
                "message_type": "sticker",
                "badges": [],
                "message_id": renderer.get("id", ""),
                "purchase_amount": "",
                "video_offset_ms": video_offset,
                "sticker_url": img_url,
                "alt_text": alt_text,
                "rank_number": None,
                "rank_badge_icon": None,
                "rank_badge_color": None,
            }
        except Exception as e:
            print(f"Error extracting sticker: {e}")
            return None

    def _fetch_replay_once(self):
        """获取录播弹幕（一次性）"""
        if not self._initialized:
            self._initialize()

        if not self.continuation:
            return

        try:
            all_messages = []
            while self.continuation:
                messages = self._fetch_new_messages()
                all_messages.extend(messages)
                if not self.continuation:
                    break

            if all_messages:
                new_messages = self._filter_new_messages(all_messages)
                if new_messages:
                    asyncio.run(self._send_messages(new_messages))
        except Exception as e:
            print(f"Error fetching replay: {e}")

    def _filter_new_messages(self, messages):
        """过滤出新消息"""
        new_messages = []
        for msg in messages:
            msg_id = msg.get("message_id", "")
            if msg_id and msg_id not in self.last_message_ids:
                self.last_message_ids.add(msg_id)
                new_messages.append(msg)

        # 限制发送数量，避免消息太多
        if len(new_messages) > 50:
            new_messages = new_messages[-50:]

        return new_messages

    async def _send_messages(self, messages):
        """通过WebSocket发送消息"""
        await manager.send_message(
            self.video_id,
            {
                "type": "danmaku",
                "data": messages,
            },
        )


poller = DanmakuPoller()
