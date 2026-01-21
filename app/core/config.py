from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    AUTH_SECRET: str   # 👈 ESTA LINHA É O PONTO-CHAVE

    class Config:
        env_file = ".env"
        extra = "ignore"  # 👈 ISSO EVITA ESSE ERRO PRA SEMPRE

settings = Settings()
