# backend/seed_data.py  ← 完整替换
import logging
from app.database import SessionLocal, engine, Base
from app.models.models import Channel, Platform

log = logging.getLogger(__name__)


def seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(Channel).count() == 0:
            youtube_channels = [
                # Hololive JP
                {
                    "platform": Platform.YOUTUBE,
                    "channel_id": "UC5CwaMl1eIgY8h02uZw7u8A",
                    "name": "Hoshimachi Suisei",
                    "avatar_url": "https://yt3.googleusercontent.com/ytc/AIdro_kLDBK5ksSvk5-XJ6S8e0kWfjy7mVl3jyUkgDeMQ7rlCpU=s160-c-k-c0x00ffffff-no-rj",
                    "is_active": True,
                },
                {
                    "platform": Platform.YOUTUBE,
                    "channel_id": "UCvzGlP9oQwU--Y0r9id_jnA",  # 大空スバル
                    "name": "Oozora Subaru",
                    "avatar_url": "https://yt3.googleusercontent.com/ytc/AIdro_k5mjdt1wcbaYCXKwmDpVXmSGtOc-LH3WjIyUHVC4soP28=s160-c-k-c0x00ffffff-no-rj",
                    "is_active": True,
                },
                {
                    "platform": Platform.YOUTUBE,
                    "channel_id": "UC1DCedRgGHBdm81E1llLhOQ",  # 兎田ぺこら
                    "name": "Usada Pekora",
                    "avatar_url": "https://yt3.googleusercontent.com/B-5Iau5CJVDiUOeCvCzHiwdkUijqoi2n0tNwfgIv_yDAvMbLHS4vq1IvK2RxL8y69BxTwmPhow=s160-c-k-c0x00ffffff-no-rj",
                    "is_active": True,
                },
                # Hololive EN
                {
                    "platform": Platform.YOUTUBE,
                    "channel_id": "UCL_qhgtOy0dy1Agp8vkySQg",  # Mori Calliope
                    "name": "Mori Calliope",
                    "avatar_url": "https://yt3.googleusercontent.com/ZZuzZBS3JHrZz49K3ApCYQo1NQLhN3ApfW0R9hAaIfCLMfx5YTL51bOgJv0zk6Ikdngmmn0G=s160-c-k-c0x00ffffff-no-rj",
                    "is_active": True,
                },
                {
                    "platform": Platform.YOUTUBE,
                    "channel_id": "UCL9hJsdk9eQa0IlWbFB2oRg",
                    "name": "Chouya Hanabi",
                    "avatar_url": "https://yt3.googleusercontent.com/N7qEUQMbq8z1lQdp4WBUz3vQ83gYiYmPt-alI5K1xMYnOh4uAxuQlUVPneZQKetzACogh6E_qA=s160-c-k-c0x00ffffff-no-rj",
                    "is_active": True,
                },
            ]
            for ch in youtube_channels:
                db.add(Channel(**ch))

            bilibili_channels = [
                {
                    "platform": Platform.BILIBILI,
                    "channel_id": "1203217682",  # 泽音Melody — 活跃的 VTuber
                    "name": "泽音Melody",
                    "avatar_url": "",
                    "is_active": True,
                },
                {
                    "platform": Platform.BILIBILI,
                    "channel_id": "672328094",  # 嘉然今天吃什么（大势 VTuber）
                    "name": "嘉然今天吃什么",
                    "avatar_url": "",
                    "is_active": True,
                },
                {
                    "platform": Platform.BILIBILI,
                    "channel_id": "672346917",  # 向晚大魔王
                    "name": "向晚大魔王",
                    "avatar_url": "",
                    "is_active": True,
                },
                {
                    "platform": Platform.BILIBILI,
                    "channel_id": "351609538",  # 珈乐Carol
                    "name": "珈乐Carol",
                    "avatar_url": "",
                    "is_active": True,
                },
            ]
            for ch in bilibili_channels:
                if db.query(Channel).filter_by(channel_id=ch["channel_id"]).first():
                    continue
                db.add(Channel(**ch))
            db.commit()
            log.info(f"Inserted {len(youtube_channels + bilibili_channels)} channels")
        else:
            log.info("Channels already exist, skipping channel seed")

    except Exception as e:
        db.rollback()
        log.error(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
