from pydantic_settings import BaseSettings


class S3ClientSettings(BaseSettings):
    bucket_name: str
    access_key_id: str
    secret_access_key: str
    region: str = "ru-central1"
    endpoint_url: str
