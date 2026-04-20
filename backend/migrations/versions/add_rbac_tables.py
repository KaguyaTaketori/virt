"""add_rbac_tables

Revision ID: add_rbac_001
Revises: 96586ab4644b
Create Date: 2026-04-02 14:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_rbac_001"
down_revision: Union[str, None] = "96586ab4644b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column("name", sa.String(length=50), unique=True, nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column("name", sa.String(length=100), unique=True, nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("resource", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_user_role_unique", "user_roles", ["user_id", "role_id"], unique=True
    )

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "permission_id",
            sa.Integer(),
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_role_permission_unique",
        "role_permissions",
        ["role_id", "permission_id"],
        unique=True,
    )

    op.create_table(
        "resource_acls",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resource", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("access", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_resource_acl_unique",
        "resource_acls",
        ["user_id", "resource", "resource_id"],
        unique=True,
    )
    op.create_index(
        "ix_resource_acl_lookup", "resource_acls", ["resource", "resource_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_resource_acl_lookup", table_name="resource_acls")
    op.drop_index("ix_resource_acl_unique", table_name="resource_acls")
    op.drop_table("resource_acls")

    op.drop_index("ix_role_permission_unique", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_user_role_unique", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_table("permissions")
    op.drop_table("roles")
