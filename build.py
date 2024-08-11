#!/usr/bin/env python3
"""build feed objects for radio.rumble.nyc"""
from datetime import datetime
import xml.etree.ElementTree as ET
import logging
import json
import os
import re
import sys


logger = logging.getLogger(__name__)


def _get_mime_type_from_ext(ext):
    if "mp3" in ext:
        return "audio/mpeg"
    if "wav" in ext:
        return "audio/x-wav"
    if "m4a" in ext or "aac" in ext:
        return "mpeg/m4a"
    logger.error("no mime_type found for %s", ext)
    return "unknown"


def _filepath_to_attachment(filepath):
    url = _filepath_to_attachment_url(filepath)
    audio_file_ext = os.path.splitext(filepath)[1]
    # url = f"{item_url}{audio_file_ext}"
    return [{"url": url, "mime_type": _get_mime_type_from_ext(audio_file_ext)}]


def _audio_filepath_to_json_feed_item(filepath):
    slug = _audio_filepath_to_slug(filepath)
    if not slug:
        logger.error("no slug for %s", filepath)
        return
    creation_time = os.path.getctime(filepath)

    date_published = datetime.fromtimestamp(creation_time).strftime(
        "%Y-%m-%dT%H:%M:%S-05:00"
    )
    logger.debug("date_published %s", date_published)

    item_url = _filepath_to_item_url(filepath)
    attachments = _filepath_to_attachment(filepath)
    return {
        "id": item_url,
        "url": item_url,
        "title": slug,
        "date_published": date_published,
        "attachments": attachments,
    }


def _audio_filepath_to_slug(filepath):
    try:
        slug = re.search(r"audio\/\d+/(.*)\.", filepath).group(1)
    except AttributeError:
        logger.error("cannot get slug from %s", filepath)
        return None
    logger.debug("slug %s", slug)
    return slug


def _filepath_to_item_url(filepath):
    episode_path = re.search(r"audio\/(.*)\.", filepath).group(1)

    logger.debug("episode_path: %s", episode_path)
    return f"https://radio.rumble.nyc/{episode_path}"


def _filepath_to_attachment_url(filepath):
    public_path = re.search(r"audio\/..*", filepath).group()
    # public_path = f"file/rumble-nyc-radio/{public_path}"
    return f"https://radio.rumble.nyc/{public_path}"


def _build_json_feed():
    items = []
    for dir_name, _dirs, files in os.walk("./audio"):
        for filename in files:
            filepath = f"{dir_name}/{filename}"
            item = _audio_filepath_to_json_feed_item(filepath)
            if item:
                items.append(item)
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Radio Rumble",
        "home_page_url": "https://radio.rumble.nyc",
        "feed_url": "https://radio.rumble.nyc/feed.json",
        "items": items,
        "icon": "/images/radio-rumble-nyc-logo-1.png",
    }

    return feed


def _json_feed_item_to_xml_item(json_item):
    item = ET.Element("item")
    title = ET.SubElement(item, "title")
    title.text = json_item["title"]
    pub_date = ET.SubElement(item, "pubDate")
    pub_date.text = json_item["date_published"]
    guid = ET.SubElement(item, "guid")
    guid.text = json_item["id"]
    guid.attrib["isPermaLink"] = "false"
    for att in json_item["attachments"]:
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.attrib["url"] = att["url"]
        enclosure.attrib["type"] = att["mime_type"]
        media_content = ET.SubElement(item, "media:content")
        media_content.attrib["url"] = att["url"]
        media_content.attrib["type"] = att["mime_type"]
    return item


def _json_feed_to_rss_channel(json_feed):
    channel = ET.Element("channel")
    title = ET.SubElement(channel, "title")
    title.text = json_feed["title"]
    link = ET.SubElement(channel, "link")
    link.text = json_feed["home_page_url"]
    atom_link = ET.SubElement(channel, "atom:link")
    atom_link.attrib["href"] = "https://radio.rumble.nyc/feed.xml"
    atom_link.attrib["ref"] = "self"

    itunes_image = ET.SubElement(channel, "itunes:image")
    itunes_image.attrib["href"] = json_feed["icon"]
    for json_item in json_feed["items"]:
        xml_item = _json_feed_item_to_xml_item(json_item)
        channel.append(xml_item)
    return channel


def _json_feed_to_rss_xml(json_feed):
    rss = ET.Element("rss")
    rss.attrib["version"] = "2.0"
    rss.attrib["xmlns:atom"] = "http://www.w3.org/2005/Atom"
    rss.attrib["xmlns:dc"] = "http://purl.org/dc/elements/1.1/"
    rss.attrib["xmlns:itunes"] = "http://www.itunes.com/dtds/podcast-1.0.dtd"
    rss.attrib["xmlns:media"] = "http://search.yahoo.com/mrss/"
    channel = _json_feed_to_rss_channel(json_feed)
    rss.append(channel)
    ET.indent(rss, space="\t", level=0)
    return rss


def build():
    """build feed objects"""
    json_feed = _build_json_feed()

    logger.info("writing feed.json ...")
    with open("feed.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(json_feed, indent=2))

    rss = _json_feed_to_rss_xml(json_feed)
    logger.info("writing feed.xml ...")
    ET.ElementTree(rss).write("feed.xml", encoding="utf-8")

    return json_feed


def main():
    """kick it all off"""
    logging.basicConfig(stream=sys.stdout, level="INFO")
    feed = build()
    "https://radio.rumble.nyc/file/rumble-nyc-radio/audio/2023/rumble.nyc-radio-episode-02-uk-garage-raw.wav"
    "https://radio.rumble.nyc/file/rumble-nyc-radio/audio/2023/rumble-nyc-radio-episode-02-uk-garage-raw.wav"


if __name__ == "__main__":
    main()
