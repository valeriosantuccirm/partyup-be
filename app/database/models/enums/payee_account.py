from enum import Enum


class CountryCode(Enum):
    us = "US"
    gb = "GB"
    fr = "FR"
    de = "DE"
    it = "IT"
    at = "AT"


class PayeeAccountStatus(Enum):
    ACTIVE = "ACTIVE"
    NOT_CONNECTED = "NOT_CONNECTED"
    PENDING = "PENDING"
