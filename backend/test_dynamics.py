import asyncio
import sys

sys.path.insert(0, "D:\\virt\\backend")
import os

os.chdir("D:\\virt\\backend")

import sqlite3
from bilibili_api import user, Credential
from datetime import datetime, timezone


async def test():
    conn = sqlite3.connect("streams.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT bilibili_sessdata, bilibili_bili_jct, bilibili_buvid3, bilibili_dedeuserid FROM users WHERE id=1"
    )
    row = cur.fetchone()
    conn.close()

    credential = Credential(
        sessdata=row[0], bili_jct=row[1] or "", buvid3=row[2] or "", dedeuserid=row[3]
    )

    u = user.User(uid=1203217682, credential=credential)

    offset = ""
    timestamps = []

    for page in range(1, 71):
        result = await u.get_dynamics_new(offset=offset)
        items = result.get("items") or []
        offset = result.get("offset", "")

        for item in items:
            modules = item.get("modules", {})
            author = modules.get("module_author", {})
            ts = author.get("pub_ts")
            if ts:
                try:
                    timestamps.append(int(ts))
                except (ValueError, TypeError):
                    pass

        print(f"Page {page}: {len(items)} items")

        if not items or not result.get("has_more", False):
            break
        await asyncio.sleep(0.5)

    if timestamps:
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        min_time = datetime.fromtimestamp(min_ts, tz=timezone.utc)
        max_time = datetime.fromtimestamp(max_ts, tz=timezone.utc)

        diff_days = (max_ts - min_ts) / 86400
        print(f"\nTotal dynamics: {len(timestamps)}")
        print(f"Time range: {min_time} ~ {max_time}")
        print(f"Duration: {diff_days:.1f} days ({diff_days / 30:.1f} months)")


asyncio.run(test())
