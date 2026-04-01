# backend/seed_data.py
from app.loguru_config import logger          # ← 修正：原文件错误写成 app.loggeruru_config / loggerger
from app.database import SessionLocal, engine, Base
from app.models.models import Channel, Platform


def seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(Channel).count() > 0:
            logger.info("Channels already exist, skipping channel seed")
            return

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
                "channel_id": "UCvzGlP9oQwU--Y0r9id_jnA",
                "name": "Oozora Subaru",
                "avatar_url": "https://yt3.googleusercontent.com/ytc/AIdro_k5mjdt1wcbaYCXKwmDpVXmSGtOc-LH3WjIyUHVC4soP28=s160-c-k-c0x00ffffff-no-rj",
                "is_active": True,
            },
            {
                "platform": Platform.YOUTUBE,
                "channel_id": "UC1DCedRgGHBdm81E1llLhOQ",
                "name": "Usada Pekora",
                "avatar_url": "https://yt3.googleusercontent.com/B-5Iau5CJVDiUOeCvCzHiwdkUijqoi2n0tNwfgIv_yDAvMbLHS4vq1IvK2RxL8y69BxTwmPhow=s160-c-k-c0x00ffffff-no-rj",
                "is_active": True,
            },
            # Hololive EN
            {
                "platform": Platform.YOUTUBE,
                "channel_id": "UCL_qhgtOy0dy1Agp8vkySQg",
                "name": "Mori Calliope",
                "avatar_url": "https://yt3.googleusercontent.com/ZZuzZBS3JHrZz49K3ApCYQo1NQLhN3ApfW0R9hAaIfCLMfx5YTL51bOgJv0zk6Ikdngmmn0G=s160-c-k-c0x00ffffff-no-rj",
                "is_active": True,
            },
        ]

        bilibili_channels = [
            {
                "platform": Platform.BILIBILI,
                "channel_id": "672328094",
                "name": "嘉然今天吃什么",
                "avatar_url": "",
                "is_active": True,
            },
            {
                "platform": Platform.BILIBILI,
                "channel_id": "672346917",
                "name": "向晚大魔王",
                "avatar_url": "",
                "is_active": True,
            },
            {
                "platform": Platform.BILIBILI,
                "channel_id": "351609538",
                "name": "珈乐Carol",
                "avatar_url": "",
                "is_active": True,
            },
        ]

        all_channels = youtube_channels + bilibili_channels
        for ch in all_channels:
            if not db.query(Channel).filter_by(channel_id=ch["channel_id"]).first():
                db.add(Channel(**ch))

        db.commit()
        logger.info("Inserted {} channels", len(all_channels))

    except Exception as e:
        db.rollback()
        logger.error("Seed error: {}", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()