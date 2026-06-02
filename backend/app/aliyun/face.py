from io import BytesIO
import warnings

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


def _runtime() -> util_models.RuntimeOptions:
    """创建 RuntimeOptions，忽略 SSL 错误（兼容 Python 3.14）"""
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")
    return util_models.RuntimeOptions(ignore_ssl=True)


def detect_face(image_bytes: bytes) -> dict:
    """DetectFace — 检测人脸质量"""
    client = _create_client()
    request = facebody_models.DetectFaceAdvanceRequest(
        image_urlobject=BytesIO(image_bytes)
    )
    response = client.detect_face_advance(request, _runtime())
    return response.body.to_map()


def compare_face(image_a_bytes: bytes, image_b_bytes: bytes) -> dict:
    """CompareFace — 人脸比对 1:1"""
    client = _create_client()
    request = facebody_models.CompareFaceAdvanceRequest(
        image_urlaobject=BytesIO(image_a_bytes),
        image_urlbobject=BytesIO(image_b_bytes),
    )
    response = client.compare_face_advance(request, _runtime())
    return response.body.to_map()


def detect_living_face(image_bytes: bytes) -> dict:
    """DetectLivingFace — 静默活体检测"""
    client = _create_client()
    task = facebody_models.DetectLivingFaceAdvanceRequestTasks(
        image_urlobject=BytesIO(image_bytes),
    )
    request = facebody_models.DetectLivingFaceAdvanceRequest(tasks=[task])
    response = client.detect_living_face_advance(request, _runtime())
    return response.body.to_map()


def add_face_entity(db_name: str, entity_id: str, labels: str = None) -> dict:
    """AddFaceEntity — 创建人脸实体（AddFace 前必须先调用）"""
    client = _create_client()
    request = facebody_models.AddFaceEntityRequest(
        db_name=db_name,
        entity_id=entity_id,
        labels=labels,
    )
    response = client.add_face_entity_with_options(request, _runtime())
    return response.body.to_map()


def add_face(db_name: str, entity_id: str, image_bytes: bytes) -> dict:
    """AddFace — 添加人脸到人脸库"""
    client = _create_client()
    request = facebody_models.AddFaceAdvanceRequest(
        db_name=db_name,
        entity_id=entity_id,
        image_url_object=BytesIO(image_bytes),
    )
    response = client.add_face_advance(request, _runtime())
    return response.body.to_map()


def search_face(db_name: str, image_bytes: bytes) -> dict:
    """SearchFace — 人脸搜索 1:N"""
    client = _create_client()
    request = facebody_models.SearchFaceAdvanceRequest(
        db_name=db_name,
        image_url_object=BytesIO(image_bytes),
        limit=5,
    )
    response = client.search_face_advance(request, _runtime())
    return response.body.to_map()


def create_face_db(db_name: str) -> dict:
    """CreateFaceDb — 创建人脸库"""
    client = _create_client()
    request = facebody_models.CreateFaceDbRequest(name=db_name)
    response = client.create_face_db_with_options(request, _runtime())
    return response.body.to_map()
