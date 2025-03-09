"""module to turn a list of audio paths into a JSON Feed object"""

import json
import logging
import os
import re
from typing import List, Optional


logger = logging.getLogger(__name__)


BASE_URL = "https://radio.rumble.nyc"


def _filepath_to_item_url(filepath):
    episode_path = re.search(r"audio\/(.*)\.", filepath).group(1)
    logger.debug("episode_path: %s", episode_path)
    return f"{BASE_URL}/{episode_path}"


def _object_to_attachment(obj):
    url = _filepath_to_attachment_url(obj["path"])
    audio_file_ext = os.path.splitext(obj["path"])[1]
    return [
        {
            "url": url,
            "mime_type": _get_mime_type_from_ext(audio_file_ext),
            "size_in_bytes": obj["content_length"],
        }
    ]


def _item_html(**item):
    return f"""
<div id="{item['id']}" class="json-feed-item">
<h3>{item['title']}</h3>
<audio controls class="video-js"  preload="metadata" data-setup='{{"fluid": true}}' poster="{item['image']}">
    <source src="{item['attachments'][0]['url']}" type="{item['attachments'][0]['mime_type']}"/>
</audio>
<p><{item.get('description','')}/p>
</div>
    """.strip()


def _get_mime_type_from_ext(ext):
    if "mp3" in ext:
        return "audio/mpeg"
    if "wav" in ext:
        return "audio/x-wav"
    if "m4a" in ext or "aac" in ext:
        return "audio/mp4"
    logger.error("no mime_type found for %s", ext)
    return "unknown"


def _filepath_to_episode_number_words(filepath) -> Optional[int]:
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


def _filepath_to_episode_number(filepath) -> Optional[int]:
    episode_number = _filepath_to_episode_number_words(filepath)
    if episode_number:
        return episode_number
    pattern = r"\-(\d+)"
    match = re.search(pattern, filepath)
    if match:
        return int(match.group(1))
    return None


def _match_audio_to_image_filepath(audio_file_path, image_filepath):
    image_episode_number = _filepath_to_episode_number(image_filepath)
    if image_episode_number:
        audio_episode_number = _filepath_to_episode_number(audio_file_path)
        if image_episode_number == audio_episode_number:
            return True


def _audio_filepath_to_image(audio_filepath):
    for dir_name, _dirs, files in os.walk("./images"):
        for filename in files:
            image_filepath = f"{dir_name}/{filename}"
            if _match_audio_to_image_filepath(audio_filepath, image_filepath):
                return f"{BASE_URL}/{image_filepath.replace('./', '')}"


def _filepath_to_attachment_url(filepath):
    public_path = re.search(r"audio\/..*", filepath).group()
    return f"{BASE_URL}/{public_path}"


def _audio_filepath_to_slug(filepath):
    try:
        slug = re.search(r"audio\/\d+/(.*)\.", filepath).group(1)
    except AttributeError:
        logger.error("cannot get slug from %s", filepath)
        return None
    logger.debug("slug %s", slug)
    return slug


def _object_to_json_feed_item(obj):
    slug = _audio_filepath_to_slug(obj["path"])
    if not slug:
        logger.error("no slug for %s", obj["path"])
        return {}
    date_published = obj["last_modified"].replace(microsecond=0).isoformat()
    logger.debug("date_published %s", date_published)

    item_url = _filepath_to_item_url(obj["path"])
    attachments = _object_to_attachment(obj)
    image = _audio_filepath_to_image(obj["path"])
    item = {
        "id": item_url,
        "url": item_url,
        "title": slug,
        "date_published": date_published,
        "attachments": attachments,
        "image": image,
    }
    item["content_html"] = _item_html(**item)
    return item


def _json_feed_items_from_audio_paths(objects):
    items = []
    for obj in objects:
        item = _object_to_json_feed_item(obj)
        if item:
            items.append(item)
    return sorted(items, key=lambda i: i["date_published"], reverse=True)


def build_feed(audio_paths):
    """create a JSON feed from a list of audio_paths"""
    items = _json_feed_items_from_audio_paths(audio_paths)
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Radio Rumble",
        "description": "an irregular DJ show, mostly about house music",
        "home_page_url": BASE_URL,
        "feed_url": f"{BASE_URL}/feed.json",
        "items": items,
        "icon": f"{BASE_URL}/images/radio-rumble-nyc-logo-1.png",
    }
    return feed


def write_feed(json_feed):
    """write json feed to feed.json"""
    logger.info("writing feed.json ...")
    with open("feed.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(json_feed, indent=2))
