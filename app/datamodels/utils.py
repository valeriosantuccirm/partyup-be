from starlette import status
from starlette.datastructures import UploadFile as starletteUploadFile

from app.api.exceptions.http_exc import APIException
from app.constants import USER_API_CONTEXT


def validate_fileimage_extension(
    value: starletteUploadFile | None,
) -> starletteUploadFile | None:
    if isinstance(value, starletteUploadFile):
        if value.content_type not in ("image/jpg", "image/png", "image/jpeg"):
            raise APIException(
                api_context=USER_API_CONTEXT,
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only 'PNG' and 'JPEG' format are allowed",
            )
        return value
    return value
