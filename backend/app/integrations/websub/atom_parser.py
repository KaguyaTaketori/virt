import re
from typing import Optional


class AtomParser:
    @staticmethod
    def parse_entry(html_or_text: str) -> Optional[dict]:
        video_id = None
        channel_id = None
        published = None
        updated = None
        title = None

        id_match = re.search(r"<yt:videoId>([^<]+)</yt:videoId>", html_or_text)
        if id_match:
            video_id = id_match.group(1)
        else:
            id_match = re.search(r"<id>([^<]+)</id>", html_or_text)
            if id_match:
                full_id = id_match.group(1)
                if "video:" in full_id:
                    video_id = full_id.split("video:")[-1]

        channel_match = re.search(r"<yt:channelId>([^<]+)</yt:channelId>", html_or_text)
        if channel_match:
            channel_id = channel_match.group(1)

        published_match = re.search(r"<published>([^<]+)</published>", html_or_text)
        if published_match:
            published = published_match.group(1)

        updated_match = re.search(r"<updated>([^<]+)</updated>", html_or_text)
        if updated_match:
            updated = updated_match.group(1)

        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html_or_text)
        if title_match:
            title = title_match.group(1)

        if not video_id:
            return None

        return {
            "video_id": video_id,
            "channel_id": channel_id,
            "published": published,
            "updated": updated,
            "title": title,
        }

    @staticmethod
    def extract_notifications(atom_xml: str) -> list[dict]:
        entries = re.findall(r"<entry>(.+?)</entry>", atom_xml, re.DOTALL)
        results = []
        for entry in entries:
            parsed = AtomParser.parse_entry(entry)
            if parsed:
                results.append(parsed)
        return results
