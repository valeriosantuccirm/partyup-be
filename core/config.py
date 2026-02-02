import os
from functools import lru_cache
from pathlib import Path

import firebase_admin
import stripe
from argon2 import PasswordHasher
from dotenv import load_dotenv
from elasticsearch import AsyncElasticsearch
from fastapi_mail import ConnectionConfig
from firebase_admin.credentials import Certificate
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import (
    Field,
    SecretStr,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
)
from pydantic_settings import BaseSettings
from redis import Redis

load_dotenv()


class Settings(BaseSettings):
    # DB
    DB_USER: StrictStr = Field(default=...)
    DB_NAME: StrictStr = Field(default=...)
    DB_PSW: StrictStr = Field(default=...)
    DB_HOST: StrictStr = Field(default=...)
    DB_PORT: StrictInt = Field(default=...)
    # REDIS
    REDIS_HOST: StrictStr = Field(default=...)
    REDIS_PORT: StrictInt = Field(default=...)
    REDIS_PSW: StrictStr | None = Field(default=None)
    REDIS_USER: StrictStr | None = Field(default=None)
    # AUTH
    SECRET_KEY: StrictStr = Field(default=...)
    ALGORITHM: StrictStr = Field(default=...)
    ACCESS_TOKEN_EXPIRE_SECONDS: StrictInt = Field(default=...)
    # EMAIL SENDER
    EMAIL_HOST: StrictStr = Field(default=...)
    EMAIL_PORT: StrictInt = Field(default=...)
    EMAIL_USERNAME: StrictStr = Field(default=...)
    EMAIL_PASSWORD: SecretStr
    EMAIL_FROM: StrictStr = Field(default=...)
    # ELASTICSEACRH DB
    ES_HOST: StrictStr = Field(default=...)
    ES_PORT: StrictStr = Field(default=...)
    # ELASTICSEARCH INDICES
    ES_USERS_INDEX: StrictStr = Field(default="users")
    ES_EVENTS_INDEX: StrictStr = Field(default="events")
    ES_EVENT_ATTENDEES_INDEX: StrictStr = Field(default="event_attendees")
    ES_USER_FOLLOWERS_INDEX: StrictStr = Field(default="user_followers")
    ES_USER_HIVERS_INDEX: StrictStr = Field(default="user_hivers")
    ES_HIVER_REQUESTS_INDEX: StrictStr = Field(default="hiver_requests")
    ES_MEDIA_INDEX: StrictStr = Field(default="media")
    # NOMINATIM
    NOMINATIM_URL: StrictStr = Field(
        default="https://nominatim.openstreetmap.org/search"
    )
    # FIREBASE
    TYPE: StrictStr = Field(default=...)
    PROJECT_ID: StrictStr = Field(default=...)
    PRIVATE_KEY_ID: StrictStr = Field(default=...)
    PRIVATE_KEY: StrictStr = Field(default=...)
    CLIENT_EMAIL: StrictStr = Field(default=...)
    CLIENT_ID: StrictStr = Field(default=...)
    AUTH_URI: StrictStr = Field(default=...)
    TOKEN_URI: StrictStr = Field(default=...)
    AUTH_PROVIDER_X509_CERT_URL: StrictStr = Field(default=...)
    CLIENT_X509_CERT_URL: StrictStr = Field(default=...)
    UNIVERSE_DOMAIN: StrictStr = Field(default=...)
    ## GOOGLE PUB/SUB
    GOOGLE_PROJECT_ID: StrictStr = Field(default=...)
    # ELASTIC
    GOOGLE_ELASTIC_USERS_TOPIC_ID: StrictStr = Field(default=...)
    GOOGLE_ELASTIC_HIVERS_TOPIC_ID: StrictStr = Field(default=...)
    GOOGLE_ELASTIC_EVENTS_TOPIC_ID: StrictStr = Field(default=...)
    ## STRIPE
    STRIPE_SECRET_API_KEY: StrictStr = Field(default=...)
    APP_PERC_FEE: StrictFloat = Field(default=...)
    ## MISC
    FERNET_KEY: StrictStr = Field(default=...)

    @property
    def DB_URI(cls) -> str:
        if os.environ.get("DB_URI") is None:
            return f"postgresql+asyncpg://{cls.DB_USER}:{cls.DB_PSW}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        return os.environ["DB_URI"]

    @property
    def ES_URI(cls) -> str:
        if os.environ.get("ES_URI") is None:
            return f"http://{cls.ES_HOST}:{cls.ES_PORT}"
        return os.environ["ES_URI"]

    @property
    def AWS_ENDPOINT_URL(csl) -> str | None:
        return os.environ.get("AWS_ENDPOINT_URL", default="http://localhost:4566")

    @property
    def FIREBASE_CONFIG(cls) -> dict[str, str]:
        keys: tuple[str, ...] = (
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
            "client_id",
            "auth_uri",
            "token_uri",
            "auth_provider_x509_cert_url",
            "client_x509_cert_url",
            "universe_domain",
        )
        conf: dict[str, str] = {}
        for k in keys:
            conf[k] = getattr(cls, k.upper())
        return conf

    @property
    def REDIS_URI(cls) -> str:
        private_creds: str = ""
        if cls.REDIS_PSW and cls.REDIS_USER:
            private_creds = f"{cls.REDIS_USER}:{cls.REDIS_PSW}@"
        return f"redis://{private_creds}{cls.REDIS_HOST}:{cls.REDIS_PORT}"

    @field_validator(
        "DB_PORT",
        "REDIS_PORT",
        "ACCESS_TOKEN_EXPIRE_SECONDS",
        "EMAIL_PORT",
        mode="before",
    )
    def _castint(cls, var: str) -> int:
        return int(var)

    @field_validator(
        "APP_PERC_FEE",
        mode="before",
    )
    def _castfloat(cls, var: float) -> float:
        return float(var)


@lru_cache
def _settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


settings: Settings = _settings()
# Stripe
stripe.api_key = settings.STRIPE_SECRET_API_KEY
# init AsyncElasticsearch
es: AsyncElasticsearch = AsyncElasticsearch(hosts=[settings.ES_URI])
# TODO: init GC Storage
# init Redis
redis: Redis = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PSW,
)
# init Firebase FCM
fcm_cred: Certificate = Certificate(
    f"{Path(__file__).resolve().cwd()!s}/.creds/partyup-be-aaf0d-firebase-adminsdk-fbsvc-6059566557.json"
)
firebase_admin.initialize_app(credential=fcm_cred)  # type: ignore
# Email config
emailenv = Environment(
    loader=PackageLoader(package_name="app", package_path="templates"),
    autoescape=select_autoescape(enabled_extensions=["html", "xml"]),
)
emailconfig = ConnectionConfig(
    MAIL_USERNAME=settings.EMAIL_USERNAME,
    MAIL_PASSWORD=settings.EMAIL_PASSWORD,
    MAIL_FROM=f"PartyUp <{settings.EMAIL_FROM}>",
    MAIL_PORT=settings.EMAIL_PORT,
    MAIL_SERVER=settings.EMAIL_HOST,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)
# password hasher
ph = PasswordHasher(
    time_cost=3,  # number of iterations
    memory_cost=64 * 1024,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)
