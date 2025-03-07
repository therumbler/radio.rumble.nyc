#!/usr/bin/env python3
"""build feed objects for radio.rumble.nyc"""
from datetime import datetime
import xml.etree.ElementTree as ET
import logging
import json
import os
import re
import sys

import boto3

logger = logging.getLogger(__name__)


class FeedBuilder:
    """Builds XML and JSON feeds for radio.rumble.nyc"""

    def __init__(self):
        self._bucket_name = "rumble-nyc-radio"
        self._s3 = self._get_s3_client()
        self._bucket = self._s3.Bucket(self._bucket_name)

    @classmethod
    def _get_s3_client(cls):
        return boto3.resource(
            service_name="s3",
            endpoint_url=os.environ["AWS_ENDPOINT_URL"],
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            region_name="auto",
        )

    @classmethod
    def _get_mime_type_from_ext(cls, ext):
        if "mp3" in ext:
            return "audio/mpeg"
        if "wav" in ext:
            return "audio/x-wav"
        if "m4a" in ext or "aac" in ext:
            return "mpeg/m4a"
        logger.error("no mime_type found for %s", ext)
        return "unknown"

    @classmethod
    def _filepath_to_attachment(cls, filepath):
        url = cls._filepath_to_attachment_url(filepath)
        audio_file_ext = os.path.splitext(filepath)[1]
        # url = f"{item_url}{audio_file_ext}"
        return [{"url": url, "mime_type": cls._get_mime_type_from_ext(audio_file_ext)}]

    def _last_modified_from_s3(self, filepath):
        resp = self._s3.Object(self._bucket_name, filepath)
        return resp.last_modified

    def _date_published_from_filepath(self, filepath):
        try:
            creation_time = os.path.getctime(filepath)
        except FileNotFoundError:
            creation_time = self._last_modified_from_s3(filepath)

        if isinstance(creation_time, int):
            date_published = datetime.fromtimestamp(creation_time).strftime(
                "%Y-%m-%dT%H:%M:%S-05:00"
            )
        else:
            date_published = creation_time.strftime("%Y-%m-%dT%H:%M:%S-05:00")
        return date_published

    def _audio_filepath_to_json_feed_item(self, filepath):
        slug = self._audio_filepath_to_slug(filepath)
        if not slug:
            logger.error("no slug for %s", filepath)
            return
        date_published = self._date_published_from_filepath(filepath)
        logger.debug("date_published %s", date_published)

        item_url = self._filepath_to_item_url(filepath)
        attachments = self._filepath_to_attachment(filepath)
        return {
            "id": item_url,
            "url": item_url,
            "title": slug,
            "date_published": date_published,
            "attachments": attachments,
        }

    @classmethod
    def _audio_filepath_to_slug(cls, filepath):
        try:
            slug = re.search(r"audio\/\d+/(.*)\.", filepath).group(1)
        except AttributeError:
            logger.error("cannot get slug from %s", filepath)
            return None
        logger.debug("slug %s", slug)
        return slug

    @classmethod
    def _filepath_to_item_url(cls, filepath):
        episode_path = re.search(r"audio\/(.*)\.", filepath).group(1)

        logger.debug("episode_path: %s", episode_path)
        return f"https://radio.rumble.nyc/{episode_path}"

    @classmethod
    def _filepath_to_attachment_url(cls, filepath):
        public_path = re.search(r"audio\/..*", filepath).group()
        return f"https://radio.rumble.nyc/{public_path}"

    @classmethod
    def _filter_audio_s3_objects(cls, o):
        if ".bzEmpty" in o.key:
            return False
        if o.key.startswith("audio/"):
            return True
        return False

    def _get_audio_from_s3(self):
        objects = self._bucket.objects.limit(400)

        # return [o for o in objects if o.key.startswith("audio/")]
        return list(filter(self._filter_audio_s3_objects, objects))

    def _get_items_from_s3(self):
        audio = self._get_audio_from_s3()

        items = []
        for a in audio:
            item = self._audio_filepath_to_json_feed_item(a.key)
            if item:
                items.append(item)
        return sorted(items, key=lambda i: i["date_published"], reverse=True)

    def _get_audio_from_filepath(self, filepath):
        items = []
        for dir_name, _dirs, files in os.walk(filepath):
            for filename in files:
                filepath = f"{dir_name}/{filename}"
                item = self._audio_filepath_to_json_feed_item(filepath)
                if item:
                    items.append(item)
        return sorted(items, key=lambda i: i["date_published"], reverse=True)

    def _build_json_feed(self):
        items = self._get_items_from_s3()

        feed = {
            "version": "https://jsonfeed.org/version/1.1",
            "title": "Radio Rumble",
            "home_page_url": "https://radio.rumble.nyc",
            "feed_url": "https://radio.rumble.nyc/feed.json",
            "items": items,
            "icon": "/images/radio-rumble-nyc-logo-1.png",
        }

        return feed

    @classmethod
    def _json_feed_item_to_xml_item(cls, json_item):
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

    @classmethod
    def _json_feed_to_rss_channel(cls, json_feed):
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
            xml_item = cls._json_feed_item_to_xml_item(json_item)
            channel.append(xml_item)
        return channel

    @classmethod
    def _json_feed_to_rss_xml(cls, json_feed):
        rss = ET.Element("rss")
        rss.attrib["version"] = "2.0"
        rss.attrib["xmlns:atom"] = "http://www.w3.org/2005/Atom"
        rss.attrib["xmlns:dc"] = "http://purl.org/dc/elements/1.1/"
        rss.attrib["xmlns:itunes"] = "http://www.itunes.com/dtds/podcast-1.0.dtd"
        rss.attrib["xmlns:media"] = "http://search.yahoo.com/mrss/"
        channel = cls._json_feed_to_rss_channel(json_feed)
        rss.append(channel)
        ET.indent(rss, space="\t", level=0)
        return rss

    def build(self):
        """build feed objects"""
        json_feed = self._build_json_feed()
        # return
        logger.info("writing feed.json ...")
        with open("feed.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(json_feed, indent=2))

        rss = self._json_feed_to_rss_xml(json_feed)
        logger.info("writing feed.xml ...")
        ET.ElementTree(rss).write("feed.xml", encoding="utf-8")

        return json_feed


def main():
    """kick it all off"""
    logging.basicConfig(stream=sys.stdout, level="INFO")
    builder = FeedBuilder()
    feed = builder.build()
    "https://radio.rumble.nyc/file/rumble-nyc-radio/audio/2023/rumble.nyc-radio-episode-02-uk-garage-raw.wav"
    "https://radio.rumble.nyc/file/rumble-nyc-radio/audio/2023/rumble-nyc-radio-episode-02-uk-garage-raw.wav"


if __name__ == "__main__":
    main()
