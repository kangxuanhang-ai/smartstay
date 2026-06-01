import base64
import json
from io import BytesIO
from typing import Optional

from alibabacloud_facebody20191230.client import Client as FacebodyClient
from alibabacloud_facebody20191230 import models as facebody_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

from app.core.config import settings


def _create_client() -> FacebodyClient:
    config = open_api_models.Config(
        access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET,
    )
    config.endpoint = f"facebody.{settings.ALIYUN_REGION_ID}.aliyuncs.com"
    return FacebodyClient(config)


def detect_face(image_bytes: bytes) -> dict:
    client = _create_client()
    request = facebody_models.DetectFaceRequest(
        image_url_or_buf=BytesIO(image_bytes)
    )
    runtime = util_models.RuntimeOptions()
    response = client.detect_face_with_options(request, runtime)
    return response.body.to_map()


def compare_face(image_a_bytes: bytes, image_b_bytes: bytes) -> dict:
    client = _create_client()
    request = facebody_models.CompareFaceRequest(
        image_url_or_buf_a=BytesIO(image_a_bytes),
        image_url_or_buf_b=BytesIO(image_b_bytes),
    )
    runtime = util_models.RuntimeOptions()
    response = client.compare_face_with_options(request, runtime)
    return response.body.to_map()


def detect_living_face(image_bytes: bytes) -> dict:
    client = _create_client()
    request = facebody_models.DetectLivingFaceRequest(
        image_url_or_buf=BytesIO(image_bytes)
    )
    runtime = util_models.RuntimeOptions()
    response = client.detect_living_face_with_options(request, runtime)
    return response.body.to_map()


def add_face(db_name: str, entity_id: str, image_bytes: bytes) -> dict:
    client = _create_client()
    request = facebody_models.AddFaceRequest(
        db_name=db_name,
        entity_id=entity_id,
        image_url_or_buf=BytesIO(image_bytes),
    )
    runtime = util_models.RuntimeOptions()
    response = client.add_face_with_options(request, runtime)
    return response.body.to_map()


def search_face(db_name: str, image_bytes: bytes) -> dict:
    client = _create_client()
    request = facebody_models.SearchFaceRequest(
        db_name=db_name,
        image_url_or_buf=BytesIO(image_bytes),
        max_num_return=5,
    )
    runtime = util_models.RuntimeOptions()
    response = client.search_face_with_options(request, runtime)
    return response.body.to_map()


def create_face_db(db_name: str) -> dict:
    client = _create_client()
    request = facebody_models.CreateFaceDbRequest(name=db_name)
    runtime = util_models.RuntimeOptions()
    response = client.create_face_db_with_options(request, runtime)
    return response.body.to_map()
