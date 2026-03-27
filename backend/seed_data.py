# backend/seed_data.py  ← 完整替换
from app.database import SessionLocal, engine, Base
from app.models.models import Channel, Platform


def seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 分别判断 channels 和 streams，避免重复 seed 任意一张表
        if db.query(Channel).count() == 0:
            # backend/seed_data.py  ← channels_data 部分替换
            channels_data = [
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
                    "channel_id": "UCL9hJsdk9eQa0IlWbFB2oRg",  # 自行替换成你想追踪的
                    "name": "Chouya Hanabi",
                    "avatar_url": "https://yt3.googleusercontent.com/N7qEUQMbq8z1lQdp4WBUz3vQ83gYiYmPt-alI5K1xMYnOh4uAxuQlUVPneZQKetzACogh6E_qA=s160-c-k-c0x00ffffff-no-rj",
                    "is_active": True,
                },
                # Bilibili（scheduler 会自动拉真实状态）
                {
                    "platform": Platform.BILIBILI,
                    "channel_id": "1203217682",
                    "name": "泽音Melody",
                    "avatar_url": "https://i1.hdslb.com/bfs/face/bf9ee18706751a9e21a13e6bc0d66977280165e3.jpg",
                    "is_active": True,
                },
            ]
            for ch in channels_data:
                db.add(Channel(**ch))
            db.commit()
            print(f"[Seed] Inserted {len(channels_data)} channels")
        else:
            print("[Seed] Channels already exist, skipping channel seed")

    except Exception as e:
        db.rollback()
        print(f"[Seed] Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
