from typing import Any, Dict, List
from uuid import UUID

from app.database.models.enums.event import EventStatus


def find_user_events(
    creator_guid: UUID,
    status: EventStatus | None = None,
    limit: int = 10,
    offset: int = 0,
    source: List[str] = [],
) -> Dict[str, Any]:
    base_query: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        "bool": {
            "must": [
                {
                    "term": {
                        "creator_guid": creator_guid,
                    }
                }
            ]
        }
    }
    if status:
        base_query["bool"]["must"].append(
            {
                "term": {
                    "status": status.value,
                }
            }
        )

    q: Dict[str, Any] = {
        "query": base_query,
        "sort": [
            {
                "created_at": {
                    "order": "desc",
                },  # Sort by newest
            }
        ],
        "size": limit,
        "from": offset,
    }
    if source:
        q["_source"] = source
    return q


def build_leaderboard_events(
    creator_guid: UUID,
    status: EventStatus,
    user_bio: str | None,
    user_lat: float,
    user_lon: float,
    radius: int = 10,
    limit: int = 10,
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
                        "must": [
                            {
                                "term": {
                                    "status": status.value,
                                },
                            }
                        ],
                        "must_not": [
                            {
                                "term": {
                                    "creator_guid": creator_guid,
                                },
                            }
                        ],
                        "should": [
                            {
                                "multi_match": {
                                    "query": user_bio,
                                    "fields": ["title^3", "description^2", "tags^2"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                }
                            }
                        ],
                        "minimum_should_match": 0,
                    }
                },
                "functions": [
                    {
                        "gauss": {
                            "location": {
                                "origin": f"{user_lat},{user_lon}",
                                "scale": radius,
                                "offset": radius / 4,
                                "decay": 0.5,
                            }
                        }
                    },
                    {
                        "field_value_factor": {
                            "field": "creator_popularity_score",
                            "factor": 1.2,
                            "modifier": "sqrt",
                            "missing": 1,
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
                "creator_popularity_score": "desc",
            },
        ],
    }
    if source:
        q["_source"] = source
    return q


def search_events(
    creator_guid: UUID,
    status: EventStatus,
    user_input: str,
    user_bio: str | None,
    user_lat: float,
    user_lon: float,
    user_location_name: str | None,
    radius: int = 10,
    limit: int = 10,
    offset: int = 0,
    source: List[str] = [],
) -> Dict[str, Any]:
    q: Dict[str, Any] = {
        "size": limit,
        "from": offset,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": user_input,
                            "fields": ["title^3", "description^2", "tags^2", "location_name"],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                        }
                    },
                    {
                        "term": {
                            "status": status.value,
                        },
                    },
                ],
                "must_not": [
                    {
                        "term": {
                            "creator_guid": creator_guid,
                        },
                    },
                ],
                "should": [
                    {
                        "function_score": {
                            "query": {
                                "match": {
                                    "bio": user_bio,
                                },
                            },
                            "boost": 3,
                        },
                    },
                    {
                        "function_score": {
                            "gauss": {
                                "location": {
                                    "origin": {
                                        "lat": user_lat,
                                        "lon": user_lon,
                                    },
                                    "scale": f"{radius}km",
                                }
                            },
                            "boost": 2,
                        }
                    },
                    {
                        "function_score": {
                            "field_value_factor": {
                                "field": "creator_popularity_score",
                                "factor": 1.2,
                                "modifier": "sqrt",
                                "missing": 1,
                            },
                            "boost": 1,
                        }
                    },
                ],
                "minimum_should_match": 1,
                "filter": [
                    {
                        "bool": {
                            "should": [
                                {
                                    "bool": {
                                        "must": [
                                            {
                                                "match": {
                                                    "location_name": user_location_name,
                                                },
                                            },
                                        ],
                                    },
                                },
                                {
                                    "bool": {
                                        "must": [
                                            {
                                                "geo_distance": {
                                                    "distance": f"{radius}km",
                                                    "location": {
                                                        "lat": user_lat,
                                                        "lon": user_lon,
                                                    },
                                                }
                                            }
                                        ]
                                    }
                                },
                            ]
                        }
                    }
                ],
            }
        },
        "sort": [
            {
                "_score": "desc",
            },
            {
                "creator_popularity_score": "desc",
            },
        ],
    }
    if source:
        q["_source"] = source
    return q


def find_event_attendees(
    event_guid: UUID,
    user_guids: List[UUID],
    source: List[str] = [],
) -> Dict[str, Any]:
    q: Dict[str, Any] = {
        "bool": {
            "must": [
                {
                    "term": {
                        "event_guid": event_guid,
                    },
                }
            ],
            "should": [
                {
                    "term": {
                        "user_guid": guid,
                    },
                }
                for guid in user_guids
            ],
            "minimum_should_match": 1,
        }
    }
    if source:
        q["_source"] = source
    return q
