"""regenerate_channel_snowflake_ids - 为现有数据生成雪花 ID

Revision ID: regenerate_channel_snowflake_ids
Revises: 449e271ec16e
Create Date: 2026-04-15

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

console = Console(force_terminal=True)

revision: str = "regenerate_channel_snowflake_ids"
down_revision: Union[str, None] = "449e271ec16e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SNOWFLAKE_EPOCH = 1704067200000
MAX_SEQUENCE = 4095


def generate_snowflake_id(sequence: int, last_timestamp: int) -> tuple[int, int, int]:
    import time

    worker_id = 1
    datacenter_id = 1

    current_timestamp = int(time.time() * 1000)

    if current_timestamp == last_timestamp:
        sequence = (sequence + 1) & MAX_SEQUENCE
        if sequence == 0:
            current_timestamp = int(time.time() * 1000)
            while current_timestamp <= last_timestamp:
                import time as time_module

                time_module.sleep(0.001)
                current_timestamp = int(time_module.time() * 1000)
    else:
        sequence = 0

    last_timestamp = current_timestamp

    snowflake_id = (
        ((current_timestamp - SNOWFLAKE_EPOCH) << 22)
        | (datacenter_id << 17)
        | (worker_id << 12)
        | sequence
    )

    return snowflake_id, sequence, last_timestamp


def upgrade() -> None:
    console.print("[bold cyan]开始重新生成 Channel 雪花 ID[/bold cyan]")

    connection = op.get_bind()

    console.print("\n[bold yellow][1/7][/bold yellow] 统计当前数据...")
    ch_count = connection.execute(sa.text("SELECT COUNT(*) FROM channels")).scalar()
    stream_count = connection.execute(sa.text("SELECT COUNT(*) FROM streams")).scalar()
    video_count = connection.execute(sa.text("SELECT COUNT(*) FROM videos")).scalar()

    try:
        dynamic_count = (
            connection.execute(
                sa.text("SELECT COUNT(*) FROM bilibili_dynamics")
            ).scalar()
            or 0
        )
    except Exception:
        dynamic_count = 0

    console.print(
        f"  [dim]channels: {ch_count}, streams: {stream_count}, videos: {video_count}, dynamics: {dynamic_count}[/dim]"
    )

    console.print("\n[bold yellow][2/7][/bold yellow] 获取现有 Channel ID 列表...")
    result = connection.execute(sa.text("SELECT id FROM channels ORDER BY id"))
    old_ids = [row[0] for row in result.fetchall()]
    console.print(f"  [dim]找到 {len(old_ids)} 个 Channel ID[/dim]")

    console.print("\n[bold yellow][3/7][/bold yellow] 生成新的雪花 ID...")
    id_mapping = {}
    sequence = 0
    last_timestamp = 0

    for old_id in old_ids:
        new_id, sequence, last_timestamp = generate_snowflake_id(
            sequence, last_timestamp
        )
        id_mapping[old_id] = new_id

    console.print(f"  [dim]生成了 {len(id_mapping)} 个新 ID[/dim]")

    console.print("\n[bold yellow][4/7][/bold yellow] 更新 streams 表...")
    for old_id, new_id in id_mapping.items():
        connection.execute(
            sa.text(
                "UPDATE streams SET channel_id = :new_id WHERE channel_id = :old_id"
            ),
            {"new_id": new_id, "old_id": old_id},
        )
    connection.commit()
    console.print("  [dim]已更新 streams[/dim]")

    console.print("\n[bold yellow][5/7][/bold yellow] 更新 videos 表 (240k+ 条记录)...")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]更新 videos...", total=video_count)

        for old_id, new_id in id_mapping.items():
            result = connection.execute(
                sa.text(
                    "UPDATE videos SET channel_id = :new_id WHERE channel_id = :old_id"
                ),
                {"new_id": new_id, "old_id": old_id},
            )
            progress.advance(task, result.rowcount or 0)

        connection.commit()

    console.print("  [dim]已更新 videos[/dim]")

    if dynamic_count > 0:
        console.print("\n[bold yellow][6/7][/bold yellow] 更新 bilibili_dynamics 表...")
        for old_id, new_id in id_mapping.items():
            connection.execute(
                sa.text(
                    "UPDATE bilibili_dynamics SET channel_id = :new_id WHERE channel_id = :old_id"
                ),
                {"new_id": new_id, "old_id": old_id},
            )
        connection.commit()
        console.print("  [dim]已更新 bilibili_dynamics[/dim]")
    else:
        console.print(
            "\n[bold yellow][6/7][/bold yellow] 跳过 bilibili_dynamics (无数据)"
        )

    console.print("\n[bold yellow][7/7][/bold yellow] 更新 channels 主键...")
    for old_id, new_id in id_mapping.items():
        connection.execute(
            sa.text("UPDATE channels SET id = :new_id WHERE id = :old_id"),
            {"new_id": new_id, "old_id": old_id},
        )
    connection.commit()
    console.print("  [dim]已更新 channels[/dim]")

    console.print("\n[bold yellow]验证数据...[/bold yellow]")
    new_ch_count = connection.execute(sa.text("SELECT COUNT(*) FROM channels")).scalar()
    new_video_ch_count = connection.execute(
        sa.text("SELECT COUNT(DISTINCT channel_id) FROM videos")
    ).scalar()
    new_stream_ch_count = connection.execute(
        sa.text("SELECT COUNT(DISTINCT channel_id) FROM streams")
    ).scalar()

    console.print(f"  [dim]channels: {new_ch_count}[/dim]")
    console.print(f"  [dim]videos 独立 channel 数: {new_video_ch_count}[/dim]")
    console.print(f"  [dim]streams 独立 channel 数: {new_stream_ch_count}[/dim]")

    result = connection.execute(
        sa.text("SELECT id, platform FROM channels ORDER BY id LIMIT 5")
    )
    console.print("\n[dim]新的 Channel ID 样例:[/dim]")
    for row in result.fetchall():
        console.print(f"  [dim]id: {row[0]}, platform: {row[1]}[/dim]")

    console.print("\n[bold green]雪花 ID 重新生成完成![/bold green]\n")


def downgrade() -> None:
    console.print("\n[bold yellow]警告: 此迁移不支持回滚![/bold yellow]")
    console.print("[dim]如果需要回滚，请从备份数据库恢复[/dim]")
