from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    class Config:
        env_file = '.env'

@lru_cache()
def get_setting():
    return Settings()