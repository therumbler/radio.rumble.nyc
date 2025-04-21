"""crawls an S3 bucket for audio files and returns a list of the paths"""

import logging
import os

import boto3

logger = logging.getLogger(__name__)


def _filename_to_content_type(filename):
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


def _filter_audio_s3_objects(o):
    if ".bzEmpty" in o.key:
        return False
    if o.key.startswith("audio/"):
        return True
    return False


def _s3_object_to_dict(obj):
    return {
        "path": obj.key,
        "content_length": obj.size,
        "last_modified": obj.last_modified,
    }


def _get_s3_resource():
    return boto3.resource(
        service_name="s3",
        endpoint_url=os.environ["AWS_ENDPOINT_URL"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def get_audio_from_s3(bucket_name):
    """fetch audio paths from S3 bucket"""
    resource = _get_s3_resource()
    bucket = resource.Bucket(bucket_name)
    objects = bucket.objects.limit(400)

    objects = list(filter(_filter_audio_s3_objects, objects))
    return list(map(_s3_object_to_dict, objects))


def sync_web(bucket_name):
    """send web elements to s3"""
    items = ["./public/index.html", "./public/feed.json", "./public/feed.xml"]
    resource = _get_s3_resource()
    for filepath in items:
        obj = resource.Object(bucket_name, filepath)
        content_type = _filename_to_content_type(filepath)
        logger.info("uploading %s  %s ...", content_type, filepath)
        obj.upload_file(filepath, ExtraArgs={"ContentType": content_type})
