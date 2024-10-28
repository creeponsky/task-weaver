from pydantic import BaseModel
from typing import List, Dict, Union, Any
from enum import Enum

class MediaType(Enum):
    IMAGE = "image"
    TEXT = "text"

class MediaDataType(Enum):
    URL = "url"
    BASE64 = "base64"
    PATH = "path"
    STRING = "string"
    IMAGE = "image"

class MediaDataModel(BaseModel):
    media_type: MediaType
    media_data_type: MediaDataType
    media_data: str