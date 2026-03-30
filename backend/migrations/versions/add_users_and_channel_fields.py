"""add_users_and_channel_fields

Revision ID: add_users_and_channel_fields
Revises:
Create Date: 2026-03-29

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_users_and_channel_fields"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 users 表
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 创建 user_channels 表
    op.create_table(
        "user_channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["channels.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_channel_user_status", "user_channels", ["user_id", "status"]
    )
    op.create_index(
        "ix_user_channel_unique",
        "user_channels",
        ["user_id", "channel_id", "status"],
        unique=True,
    )

    # 为 channels 表添加新字段
    op.add_column(
        "channels", sa.Column("banner_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "channels", sa.Column("twitter_url", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "channels", sa.Column("youtube_url", sa.String(length=200), nullable=True)
    )
    op.add_column("channels", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("channels", "description")
    op.drop_column("channels", "youtube_url")
    op.drop_column("channels", "twitter_url")
    op.drop_column("channels", "banner_url")

    op.drop_index("ix_user_channel_unique", table_name="user_channels")
    op.drop_index("ix_user_channel_user_status", table_name="user_channels")
    op.drop_table("user_channels")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
