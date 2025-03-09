import logging
import sys

from radiorumblenyc import crawler
from radiorumblenyc.jsonfeed import JSONFeed
from radiorumblenyc.rssfeed import json_feed_to_rss_xml

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(stream=sys.stdout, level="INFO")
    logger.info("starting main...")
    bucket_name = "rumble-nyc-radio"
    audio_paths = crawler.get_audio_from_s3(bucket_name)
    # print(audio_paths)

    builder = JSONFeed(bucket_name=bucket_name)
    json_feed = builder.build(audio_paths=audio_paths)

    xml_feed = json_feed_to_rss_xml(json_feed)

    builder.write_feed(json_feed)


if __name__ == "__main__":
    main()
