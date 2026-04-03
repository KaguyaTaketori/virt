from app.loguru_config import logger
from app.database import SessionLocal, engine, Base
from app.models.models import (
    Channel,
    Platform,
    Role,
    Permission,
    UserRole,
    RolePermission,
    User,
)
from app.config import settings
from app.auth import get_password_hash
from datetime import datetime, timezone
from sqlalchemy.orm import Session


def seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(Channel).count() > 0:
            logger.info("Channels already exist, skipping channel seed")

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


def seed_roles_and_permissions():
    db = SessionLocal()
    try:
        if db.query(Role).count() > 0:
            logger.info("Roles already exist, skipping role seed")
            return

        roles_data = [
            {"name": "superadmin", "description": "超级管理员 - 全部权限"},
            {"name": "admin", "description": "管理员 - 用户管理、频道管理"},
            {"name": "operator", "description": "运营 - 特定频道/组织的内容管理"},
            {"name": "user", "description": "注册用户 - 基本使用权限"},
        ]

        role_map = {}
        for rd in roles_data:
            role = Role(**rd, created_at=datetime.now(timezone.utc))
            db.add(role)
            db.flush()
            role_map[rd["name"]] = role.id

        permissions_data = [
            {
                "name": "system.manage",
                "description": "系统管理",
                "resource": "system",
                "action": "manage",
            },
            {
                "name": "user.manage",
                "description": "用户管理",
                "resource": "user",
                "action": "manage",
            },
            {
                "name": "user.read",
                "description": "查看用户",
                "resource": "user",
                "action": "read",
            },
            {
                "name": "channel.manage",
                "description": "频道管理",
                "resource": "channel",
                "action": "manage",
            },
            {
                "name": "channel.create",
                "description": "创建频道",
                "resource": "channel",
                "action": "create",
            },
            {
                "name": "channel.read",
                "description": "查看频道",
                "resource": "channel",
                "action": "read",
            },
            {
                "name": "organization.manage",
                "description": "组织管理",
                "resource": "organization",
                "action": "manage",
            },
            {
                "name": "content.manage",
                "description": "内容管理",
                "resource": "content",
                "action": "manage",
            },
            {
                "name": "bilibili.access",
                "description": "B站功能访问",
                "resource": "bilibili",
                "action": "access",
            },
        ]

        perm_map = {}
        for pd in permissions_data:
            perm = Permission(**pd, created_at=datetime.now(timezone.utc))
            db.add(perm)
            db.flush()
            perm_map[pd["name"]] = perm.id

        role_perms = {
            "superadmin": list(perm_map.values()),
            "admin": [
                "user.manage",
                "user.read",
                "channel.manage",
                "channel.create",
                "channel.read",
                "organization.manage",
                "content.manage",
                "bilibili.access",
            ],
            "operator": ["channel.read", "content.manage"],
            "user": ["channel.read"],
        }

        for role_name, perms in role_perms.items():
            role_id = role_map.get(role_name)
            if not role_id:
                continue
            for perm_name in perms:
                perm_id = perm_map.get(perm_name)
                if perm_id:
                    rp = RolePermission(
                        role_id=role_id,
                        permission_id=perm_id,
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(rp)

        db.commit()
        logger.info("Seeded roles and permissions")

    except Exception as e:
        db.rollback()
        logger.error("Role seed error: {}", e)
        raise
    finally:
        db.close()


def seed_superadmin():
    """创建或更新初始 superadmin 用户。"""
    username = settings.superadmin_username or "admin"
    password = settings.superadmin_password or ""
    if not password:
        logger.warning("SUPERADMIN_PASSWORD not set, skipping superadmin creation")
        return

    hashed_password = get_password_hash(password)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            existing.hashed_password = hashed_password
            db.commit()
            logger.info("Updated password for user: {}", username)
            _ensure_superadmin_role(db, existing.id)
            return

        user = User(
            username=username,
            email="admin@example.com",
            hashed_password=hashed_password,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.flush()
        _ensure_superadmin_role(db, user.id)
        db.commit()
        logger.info("Created superadmin user: {}", username)
    except Exception as e:
        db.rollback()
        logger.error("Superadmin seed error: {}", e)
        raise
    finally:
        db.close()


def _ensure_superadmin_role(db: Session, user_id: int) -> None:
    superadmin_role = db.query(Role).filter(Role.name == "superadmin").first()
    if not superadmin_role:
        return
    has = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.role_id == superadmin_role.id)
        .first()
    )
    if not has:
        db.add(
            UserRole(
                user_id=user_id,
                role_id=superadmin_role.id,
                created_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
        logger.info("Assigned superadmin role to user_id={}", user_id)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "roles":
        seed_roles_and_permissions()
    elif len(sys.argv) > 1 and sys.argv[1] == "superadmin":
        seed_superadmin()
    else:
        seed_data()
        seed_roles_and_permissions()
        seed_superadmin()
