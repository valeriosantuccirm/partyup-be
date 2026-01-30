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
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from redis import Redis

load_dotenv()


class Settings(BaseSettings):
    # DB
    DB_USER: str
    DB_NAME: str
    DB_PSW: str
    DB_HOST: str
    DB_PORT: int
    # REDIS
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PSW: str | None = None
    REDIS_USER: str | None = None
    # AUTH
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_SECONDS: int
    # EMAIL SENDER
    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: SecretStr
    EMAIL_FROM: str
    # ELASTICSEACRH DB
    ES_HOST: str
    ES_PORT: str
    # ELASTICSEARCH INDICES
    ES_USERS_INDEX: str = "users"
    ES_EVENTS_INDEX: str = "events"
    ES_EVENT_ATTENDEES_INDEX: str = "event_attendees"
    ES_USER_FOLLOWERS_INDEX: str = "user_followers"
    ES_USER_HIVERS_INDEX: str = "user_hivers"
    ES_HIVER_REQUESTS_INDEX: str = "hiver_requests"
    ES_MEDIA_INDEX: str = "media"
    # AWS
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION_NAME: str
    AWS_BUCKET_NAME: str
    # NOMINATIM
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org/search"
    # FIREBASE
    TYPE: str
    PROJECT_ID: str
    PRIVATE_KEY_ID: str
    PRIVATE_KEY: str
    CLIENT_EMAIL: str
    CLIENT_ID: str
    AUTH_URI: str
    TOKEN_URI: str
    AUTH_PROVIDER_X509_CERT_URL: str
    CLIENT_X509_CERT_URL: str
    UNIVERSE_DOMAIN: str
    ## GOOGLE PUB/SUB
    GOOGLE_PROJECT_ID: str
    # ELASTIC
    GOOGLE_ELASTIC_USERS_TOPIC_ID: str
    GOOGLE_ELASTIC_HIVERS_TOPIC_ID: str
    GOOGLE_ELASTIC_EVENTS_TOPIC_ID: str
    ## STRIPE
    STRIPE_SECRET_API_KEY: str
    APP_PERC_FEE: float
    ## MISC
    FERNET_KEY: str

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
firebase_admin.initialize_app(credential=fcm_cred)
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
