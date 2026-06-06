import os
import shutil
from pathlib import Path

import pytest

TEST_DATA_DIR = Path("data") / f"test_{os.getpid()}"
TEST_DB_PATH = TEST_DATA_DIR / "workflow.db"
TEST_UPLOAD_DIR = TEST_DATA_DIR / "uploads"
TEST_EXPORT_DIR = TEST_DATA_DIR / "exports"

TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["UPLOAD_DIR"] = TEST_UPLOAD_DIR.as_posix()
os.environ["EXPORT_DIR"] = TEST_EXPORT_DIR.as_posix()
os.environ["AI_ALLOW_MOCK"] = "true"
os.environ["JWT_SECRET"] = "test-secret"


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    yield
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
