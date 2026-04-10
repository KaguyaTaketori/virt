import xml.etree.ElementTree as ET
from app.loguru_config import logger

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt":   "http://www.youtube.com/xml/schemas/2015",
}

def parse_atom_feed(xml_body: bytes) -> list[dict]:
    """解析 YouTube Hub 推送的 Atom XML，返回 entry 列表。"""
    if not xml_body:
        return []
    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError as e:
        logger.error("XML 解析失败: {}", e)
        return []

    return [
        {
            "video_id":   vid_el.text.strip(),
            "channel_id": ch_el.text.strip(),
            "title":      title_el.text.strip() if title_el is not None else None,
        }
        for entry in root.findall("atom:entry", _NS)
        if (vid_el := entry.find("yt:videoId", _NS)) is not None
        and (ch_el  := entry.find("yt:channelId", _NS)) is not None
        for title_el in [entry.find("atom:title", _NS)]
    ]