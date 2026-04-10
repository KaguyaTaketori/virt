from typing import Optional

from app.loguru_config import logger

DYNAMIC_TYPE_MAP = {
    "DYNAMIC_TYPE_NONE": 0,
    "DYNAMIC_TYPE_FORWARD": 1,
    "DYNAMIC_TYPE_DRAW": 2,
    "DYNAMIC_TYPE_PIC": 2,
    "DYNAMIC_TYPE_TEXT": 4,
    "DYNAMIC_TYPE_VIDEO": 8,
    "DYNAMIC_TYPE_ARTICLE": 4,
    "DYNAMIC_TYPE_OPUS": 2,
    "DYNAMIC_TYPE_AV": 8,
    "DYNAMIC_TYPE_UGC_SEASON": 16,
    "DYNAMIC_TYPE_MUSIC": 32,
    "DYNAMIC_TYPE_LIVE": 64,
    "DYNAMIC_TYPE_COURSE": 128,
}


class BilibiliParser:
    def parse_user_info(self, raw: dict) -> dict:
        return {
                "mid": raw.get("mid"),
                "name": raw.get("name"),
                "sex": raw.get("sex"),
                "face": raw.get("face"),
                "sign": raw.get("sign"),
                "level": raw.get("level"),
                "fans": raw.get("fans"),
                "attention": raw.get("attention"),
                "archive_count": raw.get("archive_count"),
                "article_count": raw.get("article_count"),
                "following": raw.get("following"),
                "like_num": raw.get("like_num"),
                "official_verify": raw.get("official_verify"),
            }
    
    def parse_dynamic(self, item: dict) -> Optional[dict]:
        try:
            modules = item.get("modules") or {}
            module_author = modules.get("module_author") or {}
            module_dynamic = modules.get("module_dynamic") or {}
            module_stat = modules.get("module_stat") or {}
            module_tag = modules.get("module_tag") or {}

            dynamic_id = item.get("id_str", "")
            dtype_str = item.get("type", "DYNAMIC_TYPE_NONE")
            dtype = DYNAMIC_TYPE_MAP.get(dtype_str, 0)

            jump_url = item.get("basic", {}).get("jump_url", "")
            if jump_url and jump_url.startswith("//"):
                jump_url = f"https:{jump_url}"

            uid = str(module_author.get("mid", ""))
            uname = module_author.get("name", "")
            face = module_author.get("face", "")
            timestamp = int(module_author.get("pub_ts") or 0)

            is_top = (module_tag.get("text") == "置顶") or (
                module_author.get("is_top") is True
            )

            stat = {
                "forward": module_stat.get("forward", {}).get("count", 0),
                "comment": module_stat.get("comment", {}).get("count", 0),
                "like": module_stat.get("like", {}).get("count", 0),
            }

            major = module_dynamic.get("major") or {}
            content_nodes = []
            images = []
            topic_name = (module_dynamic.get("topic") or {}).get("name", "")

            if "opus" in major:
                opus = major["opus"]
                summary = opus.get("summary") or {}
                nodes = summary.get("rich_text_nodes") or []

                for n in nodes:
                    ntype = n.get("type")
                    if ntype == "RICH_TEXT_NODE_TYPE_TEXT":
                        content_nodes.append({"type": "text", "text": n.get("text")})
                    elif ntype == "RICH_TEXT_NODE_TYPE_EMOJI":
                        emoji_data = n.get("emoji") or {}
                        content_nodes.append(
                            {
                                "type": "emoji",
                                "text": n.get("text"),
                                "url": emoji_data.get("icon_url"),
                            }
                        )
                    elif ntype == "RICH_TEXT_NODE_TYPE_AT":
                        content_nodes.append(
                            {"type": "at", "text": n.get("text"), "rid": n.get("rid")}
                        )

                pics = opus.get("pics") or []
                images = [p.get("url", "") for p in pics if p.get("url")]

            elif "archive" in major:
                archive = major["archive"]
                title = archive.get("title", "")
                desc = archive.get("desc", "")
                content_nodes.append(
                    {"type": "text", "text": f"【发布视频】{title}\n{desc}".strip()}
                )
                if archive.get("cover"):
                    images = [archive.get("cover")]

            if not content_nodes:
                self_text = (module_dynamic.get("desc") or {}).get("text", "").strip()
                if self_text:
                    content_nodes.append({"type": "text", "text": self_text})

            additional = item.get("additional") or {}
            if additional.get("type") == "ADDITIONAL_TYPE_RESERVE":
                reserve = additional.get("reserve") or {}
                reserve_title = reserve.get("title", "")
                content_nodes.append(
                    {"type": "text", "text": f"\n🗓️ 直播预约：{reserve_title}"}
                )

            repost_content = None
            orig = item.get("orig")
            if orig:
                o_modules = orig.get("modules") or {}
                o_author = (o_modules.get("module_author") or {}).get(
                    "name", "未知用户"
                )
                o_dyn = o_modules.get("module_dynamic") or {}

                o_text = ""
                o_major = o_dyn.get("major") or {}
                if "opus" in o_major:
                    o_text = o_major["opus"].get("summary", {}).get("text", "")
                else:
                    o_text = (o_dyn.get("desc") or {}).get("text", "")

                repost_content = f"@{o_author}: {o_text}"

            return {
                "dynamic_id": dynamic_id,
                "url": jump_url,
                "uid": uid,
                "uname": uname,
                "face": face,
                "type": dtype,
                "timestamp": timestamp,
                "content_nodes": content_nodes,
                "images": images,
                "repost_content": repost_content,
                "stat": stat,
                "topic": topic_name,
                "is_top": is_top,
            }

        except Exception as e:
            logger.exception(
                "解析新动态项失败: id=%s, error=%s", item.get("id_str", "unknown"), str(e)
            )
            return None
        
    def parse_video(self, v: dict) -> dict:
        return {
            "bvid": v.get("bvid"),
            "title": v.get("title"),
            "pic": v.get("pic"),
            "aid": v.get("aid"),
            "duration": v.get("length"),
            "pubdate": v.get("created"),
            "play": v.get("play"),
            "like": (v.get("stat") or {}).get("like", 0),
            "reply": v.get("comment", 0),
        }