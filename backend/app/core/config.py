from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smartstay"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/smartstay"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "smartstay-dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # 阿里云配置
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""
    ALIYUN_REGION_ID: str = "cn-shanghai"
    ALIYUN_FACE_DB_NAME: str = "smartstay_faces"

    class Config:
        env_file = ".env"


settings = Settings()
