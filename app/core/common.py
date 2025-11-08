from typing import Any, Literal, overload
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException, UploadFile
from sqlalchemy import Column, ColumnElement
from starlette import status

from app.config import s3, settings
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q
from app.database.crud.psql.psqlclient import PSQLClient
from app.database.models.elasticsearch.es_event import ESEvent
from app.database.models.psql.event import Event
from app.database.models.psql.user import User


async def is_user_unique_params_already_assigned(
    db_session: PSQLClient,
    domain_attribute_pairs: tuple[tuple[str, Any], ...],
) -> bool:
    """
    Check if a unique parameter is already assigned within a given domain.

    Args:
        :session (AsyncSession): The database session used for the query.
        :domain (str): The domain to which the attribute belongs.
        :attribute (str): The attribute to check for uniqueness.

    Returns:
        :bool: True if the parameter is already assigned, False otherwise.
    """
    clauses: list[ColumnElement[Any]] = []
    for pair in domain_attribute_pairs:
        clauses.append(getattr(User, pair[0]) == pair[1])
    count: int = await db_session.count(
        model=User,
        clauses=clauses,
    )
    return bool(count)


async def are_user_info_complete(
    user: User,
) -> bool:
    """
    Check whther an user has provided all the mandatory info.
    An user info status is considered COMPLETE when the following conditions are satisfied:
        - "first_name" must be provided
        - "last_name" must be provided
        - "date_of_birth" in format DD/MM/YYYY
        - "email_verified" must be True
        - "username" must be provided
        - "location_name" must be provided
        - "location" must be provided

    Args:
        :user (User): The logged user.

    Returns:
        :bool: True if all the conditions are satisfied. False otherwise.
    """
    return not (
        not user.first_name
        or not user.last_name
        or not user.date_of_birth
        or not user.email_verified
        or not user.username
        or not user.location_name
        or not user.location
    )


async def upload_content_to_s3(
    media_content: UploadFile,
    dirpath: Literal["user-profiles", "event-media"],
    ext: str,
) -> tuple[str, str]:
    try:
        content_data: bytes = media_content.file.read()
        content_filename: str = f"{dirpath}/{uuid4()}.{ext}"
        s3.put_object(
            Bucket=settings.AWS_BUCKET_NAME,
            Key=content_filename,
            Body=content_data,
            ContentType=media_content.content_type,
            ACL="public-read",  # Make the image publicly accessible
        )
        del content_data
        return (
            f"https://{settings.AWS_BUCKET_NAME}.s3.amazonaws.com/{content_filename}",
            content_filename,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Error uploading media content: {e!s}",
        ) from e


async def delete_content_from_s3(
    media_filename: str,
) -> None:
    try:
        s3.delete_object(
            Bucket=settings.AWS_BUCKET_NAME,
            Key=media_filename,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Error deliting media content: {e!s}",
        ) from e


async def find_es_and_psql_user_event(
    esclient: ElasticsearchClient,
    db_session: PSQLClient,
    user: User,
    event_guid: UUID,
) -> tuple[Event, ESEvent]:
    psql_event: Event | None = await db_session.find_one_or_none(
        model=Event,
        criteria=(Column("guid") == event_guid,),
    )
    if not psql_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with guid '{event_guid}' not found in PSQL DB",
        )
    q: dict[str, Any] = common_q.find_by_attr(
        creator_guid=user.guid,
        guid=psql_event.guid,
    )
    es_event: ESEvent | None = await esclient.find(
        index=settings.ES_EVENTS_INDEX,
        query=q,
        model=ESEvent,
        one=True,
    )
    if not es_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with psql guid '{event_guid}' not found in ES DB",
        )
    return psql_event, es_event


@overload
async def search_map_location(
    query: str | None,
    limit: int = 5,
) -> list[dict[str, Any]]: ...


@overload
async def search_map_location(
    query: str | None,
    limit: int = 5,
    first: bool = False,
) -> dict[str, Any] | None: ...


async def search_map_location(
    query: str | None,
    limit: int = 5,
    first: bool = False,
) -> list[dict[str, Any]] | dict[str, Any] | None:
    data: list[dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.get(
            url=settings.NOMINATIM_URL,
            params={
                "q": query,
                "format": "json",
                "addressdetails": 1,
                "limit": limit,
            },
        )
        data = response.json()
    if data and first:
        return data[0]
    if not data and first:
        return None
    return data


async def get_file_extension(
    media_filename: str | None,
) -> str:
    ext: str = ""
    if media_filename:
        splitted: list[str] = media_filename.split(sep=".")
        if len(splitted) > 1:
            ext = f".{splitted[-1]}"
    return ext
