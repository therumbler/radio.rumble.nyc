#!/usr/bin/env python3
import logging
import sys

from radiorumblenyc import s3
import radiorumblenyc.jsonfeed as jsonfeed
import radiorumblenyc.rssfeed as rssfeed
import radiorumblenyc.htmlgenerator as htmlgenerator

logger = logging.getLogger(__name__)


def main():
    """kick it all off"""
    logging.basicConfig(stream=sys.stdout, level="DEBUG")
    logger.info("starting main...")
    bucket_name = "rumble-nyc-radio"

    audio_paths = s3.get_audio_from_s3(bucket_name)
    json_feed = jsonfeed.build_feed(audio_paths=audio_paths)
    xml_feed = rssfeed.json_feed_to_rss_xml(json_feed)
    html = htmlgenerator.json_feed_to_html(json_feed)

    jsonfeed.write_feed(json_feed)
    rssfeed.write_feed(xml_feed)
    htmlgenerator.write_html(html)


if __name__ == "__main__":
    main()
