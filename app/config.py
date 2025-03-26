import os
from functools import lru_cache
from typing import Dict, Tuple

import boto3
import firebase_admin
from botocore.client import BaseClient
from dotenv import load_dotenv
from elasticsearch import AsyncElasticsearch
from fastapi_mail import ConnectionConfig
from firebase_admin import credentials
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
    def FIREBASE_CONFIG(cls) -> Dict[str, str]:
        keys: Tuple[str, ...] = (
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
        conf: Dict[str, str] = {}
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
    return Settings()


settings: Settings = _settings()
# init AsyncElasticsearch
es: AsyncElasticsearch = AsyncElasticsearch(hosts=[settings.ES_URI])
# init boto3 client
s3: BaseClient = boto3.client(
    "s3",
    endpoint_url=settings.AWS_ENDPOINT_URL,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION_NAME,
)
# init Redis
redis: Redis = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PSW,
)
# init Firebase FCM
fcm_cred = credentials.Certificate(cert=settings.FIREBASE_CONFIG)
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
