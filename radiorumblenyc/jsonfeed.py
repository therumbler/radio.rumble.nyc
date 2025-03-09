"""module to turn a list of audio paths into a JSON Feed object"""

from datetime import datetime
import json
import logging
import os
import re
from typing import List, Optional

import boto3

logger = logging.getLogger(__name__)


class JSONFeed:
    BASE_URL = "https://radio.rumble.nyc"

    def __init__(self, bucket_name):
        self._bucket_name = bucket_name
        # self._s3 = self._get_s3_client()

    @classmethod
    def _filepath_to_item_url(cls, filepath):
        episode_path = re.search(r"audio\/(.*)\.", filepath).group(1)

        logger.debug("episode_path: %s", episode_path)
        return f"{cls.BASE_URL}/{episode_path}"

    def _object_to_attachment(self, obj):
        url = self._filepath_to_attachment_url(obj["path"])
        audio_file_ext = os.path.splitext(obj["path"])[1]
        # url = f"{item_url}{audio_file_ext}"
        return [
            {
                "url": url,
                "mime_type": self._get_mime_type_from_ext(audio_file_ext),
                "size_in_bytes": obj["content_length"],
            }
        ]

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

    @classmethod
    def _get_mime_type_from_ext(cls, ext):
        if "mp3" in ext:
            return "audio/mpeg"
        if "wav" in ext:
            return "audio/x-wav"
        if "m4a" in ext or "aac" in ext:
            return "audio/mp4"
        logger.error("no mime_type found for %s", ext)
        return "unknown"

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

    def _audio_filepath_to_image(self, audio_filepath):
        for dir_name, _dirs, files in os.walk("./images"):
            for filename in files:
                image_filepath = f"{dir_name}/{filename}"
                if self._match_audio_to_image_filepath(audio_filepath, image_filepath):
                    return f"{self.BASE_URL}/{image_filepath.replace("./", "")}"

    @classmethod
    def _filepath_to_attachment_url(cls, filepath):
        public_path = re.search(r"audio\/..*", filepath).group()
        return f"{cls.BASE_URL}/{public_path}"

    @classmethod
    def _audio_filepath_to_slug(cls, filepath):
        try:
            slug = re.search(r"audio\/\d+/(.*)\.", filepath).group(1)
        except AttributeError:
            logger.error("cannot get slug from %s", filepath)
            return None
        logger.debug("slug %s", slug)
        return slug

    def _object_to_json_feed_item(self, obj):
        slug = self._audio_filepath_to_slug(obj["path"])
        if not slug:
            logger.error("no slug for %s", obj["path"])
            return {}
        date_published = obj["last_modified"]
        logger.debug("date_published %s", date_published)

        item_url = self._filepath_to_item_url(obj["path"])
        attachments = self._object_to_attachment(obj)
        image = self._audio_filepath_to_image(obj["path"])
        item = {
            "id": item_url,
            "url": item_url,
            "title": slug,
            "date_published": date_published,
            "attachments": attachments,
            "image": image,
        }
        item["content_html"] = self._item_html(**item)
        return item

    def _json_feed_items_from_audio_paths(self, objects):
        items = []
        for obj in objects:
            item = self._object_to_json_feed_item(obj)
            if item:
                items.append(item)
        return sorted(items, key=lambda i: i["date_published"], reverse=True)

    def build(self, audio_paths):
        """create a JSON feed from a list of audio_paths"""
        items = self._json_feed_items_from_audio_paths(audio_paths)
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

    def write_feed(self, json_feed):
        """write json feed to feed.json"""
        logger.info("writing feed.json ...")
        with open("feed.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(json_feed, indent=2))
