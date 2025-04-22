#!/usr/bin/env python3
"""build feed objects for radio.rumble.nyc"""
from datetime import datetime
import email
import xml.etree.ElementTree as ET
import logging
import json
import os
import re
from typing import List, Optional
from string import Template
import sys

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class FeedBuilder:
    """Builds XML and JSON feeds for radio.rumble.nyc"""

    BASE_URL = "https://radio.rumble.nyc"
    AUDIO_BASE_URL = "https://f002.backblazeb2.com/file/rumble-nyc-radio"

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
            return "audio/mp4"
            # return "audio/mp4a-latm"
        logger.error("no mime_type found for %s", ext)
        return "unknown"

    def _file_size_from_s3(self, filepath):
        resp = self._s3.Object(self._bucket_name, filepath)
        return resp.content_length

    def _filepath_to_attachment(self, filepath):
        url = self._filepath_to_attachment_url(filepath)
        audio_file_ext = os.path.splitext(filepath)[1]
        # url = f"{item_url}{audio_file_ext}"
        return [
            {
                "url": url,
                "mime_type": self._get_mime_type_from_ext(audio_file_ext),
                "size_in_bytes": self._file_size_from_s3(filepath),
            }
        ]

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

    @classmethod
    def _filepath_to_episode_number_words(cls, filepath) -> Optional[int]:
        number_words: List[str] = [
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
        ]
        for w in number_words:
            pattern = rf"ep.+\-({w})"
            match = re.search(pattern, filepath)
            if match:
                word = match.group(1)
                return number_words.index(word) + 1
        return None

    @classmethod
    def _filepath_to_episode_number(cls, filepath) -> Optional[int]:
        episode_number = cls._filepath_to_episode_number_words(filepath)
        if episode_number:
            return episode_number
        pattern = r"\-(\d+)"
        match = re.search(pattern, filepath)
        if match:
            return int(match.group(1))
        return None

    def _match_audio_to_image_filepath(self, audio_file_path, image_filepath):
        image_episode_number = self._filepath_to_episode_number(image_filepath)
        if image_episode_number:
            audio_episode_number = self._filepath_to_episode_number(audio_file_path)
            if image_episode_number == audio_episode_number:
                return True

        # try to use YYYYMMDD in the filepaths to match
        audio_date_match = re.search(r"(\d{4})(\d{2})(\d{2})", audio_file_path)
        image_date_match = re.search(r"(\d{4})(\d{2})(\d{2})", image_filepath)
        if audio_date_match and image_date_match:
            return audio_date_match.group() == image_date_match.group()
        return False

    def _audio_filepath_to_image(self, audio_filepath):
        for dir_name, _dirs, files in os.walk("./public/images"):
            for filename in files:
                image_filepath = f"{dir_name}/{filename}"
                if self._match_audio_to_image_filepath(audio_filepath, image_filepath):
                    return f"{self.BASE_URL}/{image_filepath.replace("./", "")}"

        logger.warning("no image found for %s", audio_filepath)

    def _item_html(self, **item):

        return f"""
<div id="{item['id']}" class="json-feed-item">

<h3>{item['title']}</h3>
<audio controls class="video-js"  preload="metadata" data-setup='{{"fluid": true}}' poster="{item['image']}">
			<source src="{item['attachments'][0]['url']}" type="{item['attachments'][0]['mime_type']}"/>
		</audio>
<p><{item.get('description','')}/p>

</div>
        """.strip()

    def _radio_rumble_slug_to_title(self, slug):
        episode_number = re.search(r"(\d+)", slug).group(1)
        episode_name = re.search(r"(\d+)-(.+)", slug).group(2).replace("-", " ").title()
        return f"Episode {episode_number}: {episode_name}"

    def _title_from_slug(self, slug):
        if "radio-rumble-episode" in slug:
            return self._radio_rumble_slug_to_title(slug)
        title = slug.replace("-", " ")
        title = title.replace("_", " ")
        title = title.title()
        return title

    def _audio_filepath_to_json_feed_item(self, filepath):
        logger.info("processing %s", filepath)
        slug = self._audio_filepath_to_slug(filepath)
        if not slug:
            logger.error("no slug for %s", filepath)
            return
        date_published = self._date_published_from_filepath(filepath)

        item_url = self._filepath_to_item_url(filepath)
        attachments = self._filepath_to_attachment(filepath)
        image = self._audio_filepath_to_image(filepath)
        logger.info("image: %s", image)
        title = self._title_from_slug(slug)
        logger.debug("title: %s", title)
        item = {
            "id": item_url,
            "url": item_url,
            "title": title,
            "date_published": date_published,
            "attachments": attachments,
            "image": image,
        }
        item["content_html"] = self._item_html(**item)
        return item

    @classmethod
    def _audio_filepath_to_slug(cls, filepath):
        try:
            slug = re.search(r"audio\/\d+/(.*)\.", filepath).group(1)
        except AttributeError:
            logger.error("cannot get slug from %s", filepath)
            return None
        return slug

    @classmethod
    def _filepath_to_item_url(cls, filepath):
        episode_path = re.search(r"audio\/(.*)\.", filepath).group(1)
        return f"{cls.BASE_URL}/{episode_path}"

    @classmethod
    def _filepath_to_attachment_url(cls, filepath):
        public_path = re.search(r"audio\/..*", filepath).group()
        return f"{cls.AUDIO_BASE_URL}/{public_path}"

    @classmethod
    def _filter_audio_s3_objects(cls, o):
        if ".bzEmpty" in o.key:
            return False
        if o.key.startswith("audio/"):
            return True
        return False

    def _get_audio_from_s3(self):
        objects = self._bucket.objects.limit(400)

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
            "description": "an irregular DJ show, mostly about house music",
            "home_page_url": self.BASE_URL,
            "feed_url": f"{self.BASE_URL}/feed.json",
            "items": items,
            "icon": f"{self.BASE_URL}/images/radio-rumble-nyc-logo-1.png",
        }

        return feed

    @classmethod
    def _iso_date_to_rfc822(cls, iso_datetime):
        try:
            dt = datetime.strptime(iso_datetime, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            dt = datetime.strptime(iso_datetime, "%Y-%m-%dT%H:%M:%S-05:00")
        # Convert to RFC-822 format
        return email.utils.format_datetime(dt)

    @classmethod
    def _json_feed_item_to_xml_item(cls, json_item):
        item = ET.Element("item")
        title = ET.SubElement(item, "title")
        title.text = json_item["title"]
        pub_date = ET.SubElement(item, "pubDate")
        pub_date.text = cls._iso_date_to_rfc822(json_item["date_published"])
        guid = ET.SubElement(item, "guid")
        guid.text = json_item["id"]
        guid.attrib["isPermaLink"] = "false"
        for att in json_item["attachments"]:
            enclosure = ET.SubElement(item, "enclosure")
            enclosure.attrib["url"] = att["url"]
            enclosure.attrib["type"] = att["mime_type"]
            enclosure.attrib["length"] = str(att["size_in_bytes"])
            media_content = ET.SubElement(item, "media:content")
            media_content.attrib["url"] = att["url"]
            media_content.attrib["type"] = att["mime_type"]

        return item

    @classmethod
    def _json_feed_to_rss_channel(cls, json_feed):
        channel = ET.Element("channel")
        title = ET.SubElement(channel, "title")
        title.text = json_feed["title"]
        description = ET.SubElement(channel, "description")
        description.text = json_feed["description"]
        link = ET.SubElement(channel, "link")
        link.text = json_feed["home_page_url"]
        atom_link = ET.SubElement(channel, "atom:link")
        atom_link.attrib["href"] = "https://radio.rumble.nyc/feed.xml"
        atom_link.attrib["rel"] = "self"
        atom_link.attrib["type"] = "application/rss+xml"

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

    def build(self, write_files: bool = False):
        """build feed objects"""
        json_feed = self._build_json_feed()
        rss = self._json_feed_to_rss_xml(json_feed)
        html = self._json_feed_to_html(json_feed)
        if write_files:
            self._write_files(json_feed, rss, html)
        return json_feed

    def _write_files(self, json_feed, rss, html):
        logger.info("writing feed.json ...")
        with open("./public/feed.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(json_feed, indent=2))

        logger.info("writing feed.xml ...")
        ET.ElementTree(rss).write("./public/feed.xml", encoding="utf-8")

        logger.info("writing index.html ...")
        with open("./public/index.html", "w", encoding="utf-8") as f:
            f.write(html)
        return json_feed

    def _json_feed_to_html(self, json_feed) -> str:
        previous_episodes_html = "\n".join(
            [i["content_html"] for i in json_feed["items"]]
        )
        with open("templates/index.html.tmpl", encoding="utf-8") as f:
            return Template(f.read()).safe_substitute(
                previous_episodes=previous_episodes_html
            )

    @classmethod
    def _local_audio_filepath_to_s3_key(cls, local_filepath):
        logger.info("local_filepath %s", local_filepath)

    @classmethod
    def _local_image_filepath_to_s3_key(cls, local_filepath):
        logger.info("local_filepath %s", local_filepath)
        return local_filepath.replace("./", "")

    def _sync_audio_directory(self):
        for dir_name, _dirs, files in os.walk("./audio"):
            for filename in files:
                local_filepath = f"{dir_name}/{filename}"
                s3_key = self._local_audio_filepath_to_s3_key(local_filepath)

    def _sync_image(self, filepath):
        s3_key = self._local_image_filepath_to_s3_key(filepath)
        obj = self._s3.Object(self._bucket_name, s3_key)

        try:
            _ = obj.checksum_sha1
        except ClientError:
            logger.info("object %s does not exist in s3", s3_key)
            obj.upload_file(filepath)
            logger.info("upload_file complete %s", s3_key)

    def _sync_images_directory(self):
        for dir_name, _dirs, files in os.walk("./images"):
            for filename in files:
                local_filepath = f"{dir_name}/{filename}"
                self._sync_image(local_filepath)

    @classmethod
    def _filename_to_content_type(cls, filename):
        ext = os.path.splitext(filename)[1].lower()
        if ext in [".html"]:
            return "text/html"
        elif ext in [".json"]:
            return "application/json"
        elif ext in [".xml"]:
            return "application/xml"
        elif ext in [".png"]:
            return "image/png"
        elif ext in [".jpg", ".jpeg"]:
            return "image/jpeg"
        elif ext in [".gif"]:
            return "image/gif"
        elif ext in [".css"]:
            return "text/css"
        elif ext in [".js"]:
            return "application/javascript"
        else:
            return "application/octet-stream"

    def _sync_web(self):
        """send web elements to s3"""
        items = ["index.html", "feed.json", "feed.xml"]

        for filepath in items:
            obj = self._s3.Object(self._bucket_name, filepath)

            content_type = self._filename_to_content_type(filepath)
            logger.info("uploading %s  %s ...", content_type, filepath)
            obj.upload_file(filepath, ExtraArgs={"ContentType": content_type})
            # try:
            #     checksum = obj.checksum_type
            #     logger.info("checksum %s", checksum)
            #     logger.info(obj.metadata)
            # except ClientError:
            #
            #     # obj.upload_file(filepath)

    def sync_with_s3(self):
        self._sync_images_directory()
        # self._sync_web()


def main():
    """kick it all off"""
    logging.basicConfig(stream=sys.stdout, level="INFO")

    builder = FeedBuilder()
    # builder.sync_with_s3()
    feed = builder.build(write_files=True)
    # print(feed)

    "https://radio.rumble.nyc/file/rumble-nyc-radio/audio/2023/rumble.nyc-radio-episode-02-uk-garage-raw.wav"
    "https://radio.rumble.nyc/file/rumble-nyc-radio/audio/2023/rumble-nyc-radio-episode-02-uk-garage-raw.wav"


if __name__ == "__main__":
    main()
