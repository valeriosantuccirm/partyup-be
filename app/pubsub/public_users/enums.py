from enum import Enum


class PublicUsersPubSubEvent(Enum):
    user_create = "USER-CREATE"
    user_follow = "USER-FOLLOW"
    user_unfollow = "USER-UNFOLLOW"
    hiver_request = "HIVER-REQUEST"
    user_deactivate = "USER-DEACTIVATE"
    user_update = "USER-UPDATE"
