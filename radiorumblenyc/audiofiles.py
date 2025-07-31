"""a module that attaches images to audio files"""

import logging
import os
import re
import sys
from typing import List, Optional

from mutagen.mp4 import MP4, MP4Cover, AtomDataType


logger = logging.getLogger(__name__)

BASE_URL = "./public/"


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
    # try to use YYYYMMDD in the filepaths to match
    audio_date_match = re.search(r"(\d{4})(\d{2})(\d{2})", audio_file_path)
    image_date_match = re.search(r"(\d{4})(\d{2})(\d{2})", image_filepath)
    if audio_date_match and image_date_match:
        return audio_date_match.group() == image_date_match.group()
    return False


def _audio_filepath_to_image(audio_filepath):
    for dir_name, _dirs, files in os.walk("./public/images"):
        for filename in files:
            image_filepath = f"{dir_name.replace('/public', '')}/{filename}"
            if _match_audio_to_image_filepath(audio_filepath, image_filepath):
                return f"{BASE_URL}/{image_filepath.replace('./', '')}"


def _get_image_type_from_path(filepath):
    """
    Get the image type from the file path.
    """
    image_type = None
    if filepath.endswith(".jpg"):
        image_type = AtomDataType.JPEG
    if filepath.endswith(".jpeg"):
        image_type = AtomDataType.JPEG
    elif filepath.endswith(".png"):
        image_type = AtomDataType.PNG
    elif filepath.endswith(".gif"):
        image_type = AtomDataType.GIF
    else:
        logger.error("Unsupported image type: %s", filepath)
    return image_type


def _update_audio_file_with_image(audio_file_path):
    image_path = _audio_filepath_to_image(audio_file_path)
    if not image_path:
        logger.error("Image not found for %s", audio_file_path)
        return

    audio_file = MP4(audio_file_path)
    if audio_file["covr"]:
        logger.info("File already has covr. Not updating: %s", audio_file_path)
        return
    logger.info("updating %s with image %s", audio_file_path, image_path)
    with open(image_path, "rb") as img_file:
        image_data = img_file.read()
        imageformat = _get_image_type_from_path(image_path)
        cover = MP4Cover(
            image_data,
            imageformat=imageformat,
        )

        audio_file["covr"] = [cover]
        audio_file.save()


def process_audio_paths(paths):
    """
    Process a list of audio file paths and update each audio file with its corresponding image URL.
    """
    audio_files = []
    for audio_path in paths:
        _update_audio_file_with_image(audio_path)

    return audio_files


def main():
    # Example usage
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    audio_paths = [
        "./audio/radio-rumble-ep-8-springtime-house.m4a",
    ]
    process_audio_paths(audio_paths)


if __name__ == "__main__":
    main()
