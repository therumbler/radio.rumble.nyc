"""create HTML from a JSON Feed dictionary"""

import logging
from string import Template

logger = logging.getLogger(__name__)


def json_feed_to_html(json_feed: dict) -> str:
    """Turn s JSON feed dictionary into an HTML string"""
    previous_episodes_html = "\n".join([i["content_html"] for i in json_feed["items"]])
    with open("templates/index.html.tmpl", encoding="utf-8") as f:
        return Template(f.read()).safe_substitute(
            previous_episodes=previous_episodes_html
        )


def write_html(html: str):
    """write index.html"""
    logger.info("writing index.html ...")
    with open("./public/index.html", "w", encoding="utf-8") as f:
        f.write(html)
