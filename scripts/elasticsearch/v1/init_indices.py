import os
from typing import Any, Dict

from elasticsearch import Elasticsearch


def es_uri() -> str:
    if os.environ.get("ES_URI") is None:
        return f"http://{os.environ.get('ES_HOST', default='localhost')}:{(os.environ.get('ES_PORT', default='9200'))}"
    return os.environ["ES_URI"]


ES_URI: str = es_uri()
es = Elasticsearch(hosts=[ES_URI])

## INDICES AND MAPPINGS

EVENTS_INDEX = "events"
EVENTS_MAPPING: Dict[str, Dict[str, Dict[str, Dict[str, str | int]]]] = {
    "mappings": {
        "properties": {
            "hivers_count": {"type": "integer"},
            "cover_image_filename": {"type": "keyword"},
            "cover_image_url": {"type": "keyword"},
            "currency": {"type": "keyword"},
            "created_at": {"type": "date"},
            "description": {"type": "text"},
            "end_date": {"type": "date"},
            "followers_attendees_count": {"type": "integer"},
            "is_private": {"type": "boolean"},
            "guid": {"type": "keyword"},
            "location": {"type": "geo_point"},
            "max_attendees": {"type": "integer"},
            "min_donation": {"type": "scaled_float", "scaling_factor": 100},
            "ponr": {"type": "date"},
            "public_attendees_count": {"type": "integer"},
            "start_date": {"type": "date"},
            "status": {"type": "keyword"},
            "title": {"type": "text"},
            "total_attendees_count": {"type": "integer"},
            "total_donations": {"type": "scaled_float", "scaling_factor": 100},
            "updated_at": {"type": "date"},
            "creator_guid": {"type": "keyword"},
            "creator_popularity_score": {"type": "float"},
            "tags": {"type": "keyword"},
            "hivers_reserved_slots": {"type": "integer"},
        }
    }
}


USERS_INDEX: str = "users"
USERS_MAPPINGS: Dict[str, Dict[str, Dict[str, Dict[str, str]]]] = {
    "mappings": {
        "properties": {
            "bio": {"type": "text"},
            "hivers_count": {"type": "integer"},
            "created_at": {"type": "date"},
            "date_of_birth": {"type": "keyword"},
            "email": {"type": "keyword"},
            "event_participation": {"type": "integer"},
            "first_name": {"type": "text"},
            "followers_count": {"type": "integer"},
            "following_count": {"type": "integer"},
            "full_name": {"type": "text"},
            "guid": {"type": "keyword"},
            "is_active": {"type": "boolean"},
            "last_name": {"type": "text"},
            "popularity_score": {"type": "float"},
            "posts_count": {"type": "integer"},
            "profile_image": {"type": "keyword"},
            "updated_at": {"type": "date"},
            "username": {"type": "keyword"},
            "location_name": {"type": "text"},
            "tags": {"type": "keyword"},
            "location": {"type": "geo_point"},
            "firebase_uid": {"type": "text"},
        }
    }
}


EVENT_ATTENDEES_INDEX = "event_attendees"
EVENT_ATTENDEES_MAPPINGS: Dict[str, Dict[str, Dict[str, Dict[str, str]]]] = {
    "mappings": {
        "properties": {
            "attendee_type": {"type": "keyword"},
            "created_at": {"type": "date"},
            "invitation_sent_at": {"type": "date"},
            "rsvp_date": {"type": "date"},
            "status": {"type": "keyword"},
            "event_guid": {"type": "keyword"},
            "user_guid": {"type": "keyword"},
            "guid": {"type": "keyword"},
        }
    }
}


USER_HIVERS_INDEX = "user_hivers"
USER_HIVERS_MAPPINGS: Dict[str, Dict[str, Dict[str, Dict[str, str]]]] = {
    "mappings": {
        "properties": {
            "created_at": {"type": "date"},
            "guid": {"type": "keyword"},
            "hiver_guid": {"type": "keyword"},
            "user_guid": {"type": "keyword"},
        }
    }
}


USER_FOLLOWER_INDEX = "user_followers"
USER_FOLLOWERS_MAPPINGS: Dict[str, Dict[str, Dict[str, Dict[str, str]]]] = {
    "mappings": {
        "properties": {
            "created_at": {"type": "date"},
            "guid": {"type": "keyword"},
            "follower_guid": {"type": "keyword"},
            "user_guid": {"type": "keyword"},
        }
    }
}


HIVER_REQUESTS_INDEX = "hiver_requests"
HIVER_REQUESTS_MAPPINGS: Dict[str, Dict[str, Dict[str, Dict[str, str]]]] = {
    "mappings": {
        "properties": {
            "guid": {"type": "keyword"},
            "sender_guid": {"type": "keyword"},
            "receiver_guid": {"type": "keyword"},
            "status": {"type": "keyword"},
            "created_at": {"type": "date"},
        }
    }
}

MEDIA_INDEX = "media"
MEDIA_MAPPINGS: Dict[str, Dict[str, Dict[str, Dict[str, str]]]] = {
    "mappings": {
        "properties": {
            "guid": {"type": "keyword"},
            "event_guid": {"type": "keyword"},
            "user_guid": {"type": "keyword"},
            "media_type": {"type": "keyword"},
            "created_at": {"type": "date"},
            "content_filename": {"type": "text"},
            "file_url": {"type": "text"},
            "updated_at": {"type": "date"},
        }
    }
}


ENTITIES: Dict[str, Any] = {
    EVENT_ATTENDEES_INDEX: EVENT_ATTENDEES_MAPPINGS,
    EVENTS_INDEX: EVENTS_MAPPING,
    USER_HIVERS_INDEX: USER_HIVERS_MAPPINGS,
    USER_FOLLOWER_INDEX: USER_FOLLOWERS_MAPPINGS,
    USERS_INDEX: USERS_MAPPINGS,
    HIVER_REQUESTS_INDEX: HIVER_REQUESTS_MAPPINGS,
    MEDIA_INDEX: MEDIA_MAPPINGS,
}


def create_index() -> None:
    # TODO: remove when time
    indices = list(ENTITIES.keys())
    for index in indices:
        if es.indices.exists(index=index):
            es.indices.delete(index=index)
            print(f"✅  Index '{index}' DELETED successfully.")
    # ---
    for index in indices:
        if not es.indices.exists(index=index):
            es.indices.create(index=index, body=ENTITIES[index])
            print(f"✅  Index '{index}' CREATED successfully.")
        else:
            print(f"⚠️  Index '{index}' already exists.")


if __name__ == "__main__":
    create_index()
