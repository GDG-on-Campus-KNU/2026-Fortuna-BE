import os


os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["JWT_SECRET_KEY"] = "test-runtime-secret"
os.environ["METADATA_BACKEND"] = "json"
os.environ["STORAGE_BACKEND"] = "local"
