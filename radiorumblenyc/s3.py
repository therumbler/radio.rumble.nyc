"""crawls an S3 bucket for audio files and returns a list of the paths"""

import os

import boto3


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


def get_audio_from_s3(bucket_name):
    """fetch audio paths from S3 bucket"""
    resource = boto3.resource(
        service_name="s3",
        endpoint_url=os.environ["AWS_ENDPOINT_URL"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    bucket = resource.Bucket(bucket_name)
    objects = bucket.objects.limit(400)

    objects = list(filter(_filter_audio_s3_objects, objects))
    return list(map(_s3_object_to_dict, objects))
