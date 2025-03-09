from datetime import datetime
import email
import email.utils
import logging
import xml.etree.ElementTree as ET


logger = logging.getLogger(__name__)


def json_feed_to_rss_xml(json_feed):
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


def _date_to_rfc822(iso_datetime):
    # Convert to RFC-822 format
    return email.utils.format_datetime(iso_datetime)

    try:
        dt = datetime.strptime(iso_datetime, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        dt = datetime.strptime(iso_datetime, "%Y-%m-%dT%H:%M:%S-05:00")
    # Convert to RFC-822 format
    return email.utils.format_datetime(dt)


def _json_feed_item_to_xml_item(json_item):
    item = ET.Element("item")
    title = ET.SubElement(item, "title")
    title.text = json_item["title"]
    pub_date = ET.SubElement(item, "pubDate")
    pub_date.text = _date_to_rfc822(json_item["date_published"])
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


def _json_feed_to_rss_channel(json_feed):
    """takes a JSON Feed dict and returns an RSS XML object"""
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
        xml_item = _json_feed_item_to_xml_item(json_item)
        channel.append(xml_item)
    return channel


def write_feed(self, rss_feed: ET.Element):
    """write an ET.Element object to feed.xml"""
    logger.info("writing feed.xml ...")
    ET.ElementTree(rss_feed).write("feed.xml", encoding="utf-8")
