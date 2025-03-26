from typing import Any, Dict, List, Literal
from uuid import UUID

from sqlalchemy import Column
from starlette import status

from app.api.exceptions.http_exc import APIException, DBException
from app.config import settings
from app.constants import DB_API_CONTEXT, DB_PSQL_DB_CONTEXT, USER_HIVER_API_CONTEXT
from app.core import fcm
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q, users_q
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.elasticsearch.es_hiver_request import ESHiverRequest
from app.database.models.elasticsearch.es_user import ESUser
from app.database.models.elasticsearch.es_user_hiver import ESUserHiverBase, ESUserHiverRelations
from app.database.models.enums.hiver import HiverRequestStatus
from app.database.models.psql.hiver_request import HiverRequest
from app.database.models.psql.user import User
from app.database.models.psql.user_hiver import UserHiver
from app.datamodels.schemas.response import ESListedUser, PaginatedListedUser


async def get_user_hiver_requests(
    esclient: ElasticsearchClient,
    user: User,
    status: HiverRequestStatus,
    mode: Literal["sent", "received"],
    limit: int = 20,
    offset: int = 0,
) -> List[ESHiverRequest]:
    q: Dict[str, Any] = users_q.find_user_hiver_requests(
        user_guid=user.guid,
        request_status=status,
        mode=mode,
        limit=limit,
        offset=offset,
    )
    return await esclient.find(
        index=settings.ES_HIVER_REQUESTS_INDEX,
        query=q,
        model=ESHiverRequest,
    )


async def respond_hiver_request(
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    user: User,
    hiver_request_guid: UUID,
    accept: bool,
) -> None:
    psql_hiver_request: HiverRequest | None = await db_session.find_one_or_none(
        model=HiverRequest,
        criteria=(Column("guid") == hiver_request_guid,),
    )
    if not psql_hiver_request:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_PSQL_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find hiver request in PSQL DB with guid '{hiver_request_guid}'",
        )
    if psql_hiver_request.status in (HiverRequestStatus.ACCEPTED, HiverRequestStatus.DECLINED):
        raise APIException(
            api_context=USER_HIVER_API_CONTEXT,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Hiver request already processed. Status: {psql_hiver_request.status}",
        )
    psql_sender: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("guid") == psql_hiver_request.sender_guid,),
    )
    if not psql_sender:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_PSQL_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find user in PSQL DB with guid '{psql_hiver_request.sender_guid}'",
        )
    es_hiver_request: ESHiverRequest | None = await esclient.find(
        index=settings.ES_HIVER_REQUESTS_INDEX,
        query=common_q.find_by_attr(guid=hiver_request_guid),
        model=ESHiverRequest,
        one=True,
    )
    if not es_hiver_request:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_PSQL_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find hiver request in ES DB linked to PSQL guid '{hiver_request_guid}'",
        )
    # update status of hiver request
    psql_hiver_request.status = HiverRequestStatus.ACCEPTED if accept else HiverRequestStatus.DECLINED
    # increase users hivers count if hiver request accepted
    if accept:
        es_sender: ESUser | None = await esclient.find(
            index=settings.ES_USERS_INDEX,
            query=common_q.find_by_attr(guid=psql_sender.guid),
            model=ESUser,
            one=True,
        )
        es_receiver: ESUser | None = await esclient.find(
            index=settings.ES_USERS_INDEX,
            query=common_q.find_by_attr(guid=user.guid),
            model=ESUser,
            one=True,
        )
        if not es_sender or not es_receiver:
            raise DBException(
                api_context=DB_API_CONTEXT,
                db_context=DB_PSQL_DB_CONTEXT,
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find hiver request in ES DB linked to PSQL guid '{psql_sender.guid}'",
            )
        user.hivers_count += 1
        psql_sender.hivers_count += 1
        es_sender.hivers_count += 1
        es_receiver.hivers_count += 1
        await esclient.update(
            index=settings.ES_USERS_INDEX,
            doc_id=es_sender.id,
            **es_sender.model_dump(),
        )
        await esclient.update(
            index=settings.ES_USERS_INDEX,
            doc_id=es_receiver.id,
            **es_receiver.model_dump(),
        )
        user_hiver = UserHiver(
            hiver_guid=user.guid,
            user_guid=psql_sender.guid,
        )
        await db_session.add(
            instance=user_hiver,
        )
        await esclient.add(
            index=settings.ES_USER_HIVERS_INDEX,
            instance=ESUserHiverBase(**user_hiver.model_dump()),
        )
    # update ES docs
    await esclient.update(
        index=settings.ES_HIVER_REQUESTS_INDEX,
        doc_id=es_hiver_request.id,
        status=psql_hiver_request.status.value,
    )
    if psql_sender.fcm_token:
        await fcm.send_push_notification(
            fcm_token=psql_sender.fcm_token,
            title="Hiver request update",
            body=f"Your hiver request to {user.username} has been {psql_hiver_request.status.value.lower()}",
        )


async def get_user_linked_hivers(
    esclient: ElasticsearchClient,
    user: User,
    limit: int = 20,
    offset: int = 0,
    fields: List[str] = ["username", "profile_image", "followers_count", "guid", "_id", "hivers_count", "full_name"],
) -> PaginatedListedUser:
    hivers_relations_q: Dict[str, Any] = users_q.find_user_hivers(
        psql_user_guid=user.guid,
        limit=limit,
        offset=offset,
        source=["hiver_guid", "user_guid"],
    )
    user_hivers_relations: List[ESUserHiverRelations] = await esclient.find(
        index=settings.ES_USER_HIVERS_INDEX,
        query=hivers_relations_q,
        model=ESUserHiverRelations,
    )
    relations_guids = list(
        set(
            [uh.hiver_guid for uh in user_hivers_relations if uh.hiver_guid != user.guid]
            + [uh.user_guid for uh in user_hivers_relations if uh.user_guid != user.guid]
        )
    )
    user_hivers_q: Dict[str, Any] = users_q.find_users(
        psql_guids=relations_guids,
        limit=limit,
        offset=offset,
        source=fields,
    )
    user_hivers: List[ESListedUser] = await esclient.find(
        index=settings.ES_USERS_INDEX,
        query=user_hivers_q,
        model=ESListedUser,
    )
    return PaginatedListedUser(
        total_results=len(user_hivers),
        limit=limit,
        offset=offset,
        listed_users=user_hivers,
    )
