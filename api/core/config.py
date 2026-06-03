"""
Configuration management via pydantic-settings.
All values can be overridden via environment variables or a .env file.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application
    app_name: str = "careerfit-ai"
    app_version: str = "1.0.0"
    debug: bool = False

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout: int = 120
    ollama_max_retries: int = 2

    # Sentence Transformers
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"

    # File storage
    upload_dir: Path = Path("/tmp/careerfit_ai/uploads")
    output_dir: Path = Path("/tmp/careerfit_ai/outputs")
    max_file_size_mb: int = 20
    job_ttl_seconds: int = 3600

    # Pipeline thresholds
    weak_section_threshold: float = 0.55
    strong_section_threshold: float = 0.78
    max_rewrite_retries: int = 2

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    def ensure_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
