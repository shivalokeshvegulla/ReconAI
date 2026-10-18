from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "ReconAI API"
    APP_VERSION: str = "1.0.0"    
    DEBUG: bool = False

    DATABASE_URL: str = "mysql+pymysql://bank_app:CHANGE_ME@localhost:3306/banklite"
    STORAGE_DIR: str = "storage"    
    UPLOAD_DIR: str = "storage/uploads"    
    DEFAULT_AMOUNT_TOLERANCE: str = "0.01"

    class Config:    
            env_file = ".env"    
            env_file_encoding = "utf-8"    
         
@lru_cache()    
def get_settings() -> Settings:    
    return Settings()    


