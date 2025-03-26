from typing import Any, Dict, List, Literal
from uuid import UUID

from app.database.models.enums.hiver import HiverRequestStatus


def find_users(
    psql_guids: List[UUID],
    limit: int,
    offset: int,
    source: List[str] = [],
) -> Dict[str, Any]:
    q: Dict[str, Any] = {
        "from": offset,
        "size": limit,
        "query": {
            "terms": {
                "guid": psql_guids,
            }
        },
        "sort": [
            {
                "popularity_score": {
                    "order": "desc",
                },
            },
        ],
    }
    if source:
        q["_source"] = source
    return q


def find_user_hiver_requests(
    user_guid: UUID,
    request_status: HiverRequestStatus,
    mode: Literal["sent", "received"],
    limit: int,
    offset: int,
    source: List[str] = [],
) -> Dict[str, Any]:
    _map: Dict[str, str] = {
        "sent": "sender_guid",
        "received": "receiver_guid",
    }
    q: Dict[str, Any] = {
        "size": limit,
        "from": offset,
        "query": {
            "bool": {
                "must": [
                    {
                        "bool": {
                            "should": [
                                {
                                    "term": {
                                        _map[mode]: user_guid,
                                    },
                                },
                            ],
                            "minimum_should_match": 1,
                        }
                    },
                    {
                        "term": {
                            "status": request_status.value,
                        },
                    },
                ]
            }
        },
        "sort": [
            {
                "created_at": "desc",
            },
        ],
    }
    if source:
        q["_source"] = source
    return q


def find_user_hivers(
    psql_user_guid: UUID,
    limit: int,
    offset: int,
    source: List[str] = [],
    last_sort_values: List[Any] = [],
) -> Dict[str, Any]:
    q: Dict[str, Any] = {
        "from": offset,
        "size": limit,
        "query": {
            "bool": {
                "should": [
                    {
                        "term": {
                            "user_guid": psql_user_guid,
                        },
                    },
                    {
                        "term": {
                            "hiver_guid": psql_user_guid,
                        },
                    },
                ],
                "minimum_should_match": 1,
            },
        },
        "sort": [
            {
                "created_at": "desc",
            }
        ],
    }
    if source:
        q["_source"] = source
    if last_sort_values:
        q["search_after"] = last_sort_values
    return q


def find_public_users(
    user_bio: str | None,
    user_guid: str,
    user_username: str | None,
    user_fullname: str | None,
    user_hiver_guids: List[UUID],
    user_follower_guids: List[UUID],
    user_input: str,
    user_lat: float | None,
    user_lon: float | None,
    radius: int = 50,
    limit: int = 20,
    offset: int = 0,
    source: List[str] = [],
) -> Dict[str, Any]:
    q: Dict[str, Any] = {
        "size": limit,
        "from": offset,
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {  # Strong boost for username and full_name matches
                                    "query": user_input,
                                    "fields": ["username^10", "full_name^7"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                }
                            },
                            {
                                "prefix": {
                                    "username": {
                                        "value": user_input,
                                        "boost": 15,
                                    },
                                },
                            },
                            {
                                "prefix": {
                                    "full_name": {
                                        "value": user_input,
                                        "boost": 10,
                                    },
                                },
                            },
                            {
                                "match": {
                                    "bio": {
                                        "query": user_bio,
                                        "boost": 2,
                                    },
                                },
                            },
                            # Friends & followers get a priority boost
                            {
                                "terms": {
                                    "user_guid": user_hiver_guids,
                                    "boost": 3,
                                },
                            },
                            {
                                "terms": {
                                    "user_guid": user_follower_guids,
                                    "boost": 2,
                                },
                            },
                        ],
                        "minimum_should_match": 1,  # Must match at least one condition
                        "must_not": [
                            {
                                "terms": {
                                    "user_guid": user_hiver_guids,
                                },
                            },
                            {
                                "terms": {
                                    "user_guid": user_follower_guids,
                                },
                            },
                            {
                                "term": {
                                    "guid": user_guid,
                                },
                            },  # Exclude the current user
                        ],
                    }
                },
                "functions": [
                    {
                        "field_value_factor": {
                            "field": "popularity_score",  # Popularity matters
                            "factor": 2,
                            "modifier": "sqrt",
                            "missing": 1,
                        }
                    },
                    {
                        "gauss": {
                            "updated_at": {  # Boost for recent user activity
                                "origin": "now",
                                "scale": "30d",
                                "offset": "7d",
                                "decay": 0.5,
                            },
                        },
                    },
                    {
                        "gauss": {
                            "location": {  # Proximity relevance
                                "origin": {
                                    "lat": user_lat,
                                    "lon": user_lon,
                                },
                                "scale": f"{radius}km",
                            }
                        }
                    },
                    {
                        "script_score": {  # Extra boost if username or full name matches exactly
                            "script": {
                                "source": """
                                double username_boost = params.username_match ? 3 : 1;
                                double full_name_boost = params.fullname_match ? 2.5 : 1;
                                return _score * username_boost * full_name_boost;
                            """,
                                "params": {
                                    "username_match": user_input in str(user_username),
                                    "fullname_match": user_input in str(user_fullname),
                                },
                            }
                        }
                    },
                ],
                "score_mode": "sum",
                "boost_mode": "sum",
            }
        },
        "sort": [
            {
                "_score": "desc",
            },
            {
                "popularity_score": "desc",
            },
        ],
    }
    if source:
        q["_source"] = source
    return q


def find_linked_users_ids(
    left_index: str,
    right_index: str,
    left_term: Dict[str, Any],
    right_term: Dict[str, Any],
    left_source: List[str] = [],
    right_source: List[str] = [],
) -> List[Dict[str, Any]]:
    qs: List[Dict[str, Any]] = [
        {
            "index": left_index,
        },
        {
            "query": {
                "term": left_term,
            },
        },
        {
            "index": right_index,
        },
        {
            "query": {
                "term": right_term,
            },
        },
    ]
    if left_source:
        qs[1]["_source"] = left_source
    if right_source:
        qs[3]["_source"] = right_source
    return qs


# async def es_find_user_hivers(
#     psql_user_guid: UUID,
#     fields: list[str],
#     limit: int = 20,
#     offset: int = 0,
# ) -> List[ESListedUser]:
#     query: Dict[str, Any] = {
#         "from": offset,
#         "size": limit,
#         "query": {
#             "bool": {
#                 "should": [
#                     {
#                         "term": {
#                             "user_guid": psql_user_guid,
#                         },
#                     },
#                     {
#                         "term": {
#                             "hiver_guid": psql_user_guid,
#                         },
#                     },
#                 ],
#                 "minimum_should_match": 1,
#             },
#         },
#         "_source": ["hiver_guid", "user_guid"],
#     }
#     response: ObjectApiResponse[Any] = es.search(
#         index=USER_HIVERS_INDEX,
#         body=query,
#     )
#     # Extract hiver_guid values from matching documents
#     hiver_guids = list(
#         set(
#             [
#                 hit["_source"]["hiver_guid"]
#                 for hit in response["hits"]["hits"]
#                 if hit["_source"]["hiver_guid"] != str(psql_user_guid)
#             ]
#             + [
#                 hit["_source"]["user_guid"]
#                 for hit in response["hits"]["hits"]
#                 if hit["_source"]["user_guid"] != str(psql_user_guid)
#             ]
#         )
#     )
#     user_query: Dict[str, Any] = {
#         "from": offset,
#         "size": limit,
#         "query": {"terms": {"guid": hiver_guids}},
#         "sort": [
#             {
#                 "popularity_score": {
#                     "order": "desc",
#                 },
#             },
#         ],
#         "_source": fields,
#     }
#     user_response: ObjectApiResponse[Any] = es.search(
#         index=USERS_INDEX,
#         body=user_query,
#     )
#     users: List[Dict[str, Any]] = [{"id": hit["_id"], **hit["_source"]} for hit in user_response["hits"]["hits"]]
#     return [ESListedUser(**user) for user in users]
