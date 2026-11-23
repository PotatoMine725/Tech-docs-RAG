import os

import pytest


@pytest.fixture(autouse=True)
def _restore_environment():
    """Each test starts from the environment pytest started with.

    Importing `markitdown` calls `load_dotenv()`, which copies the developer's real `.env` (EMBEDDING_PROVIDER, ...)
    into `os.environ` for the rest of the process; later tests would then read local settings (e.g. the gate threshold
    of another embedding provider). Restoring after every test keeps offline tests independent of that file.
    """
    saved = dict(os.environ)
    yield
    if os.environ != saved:
        os.environ.clear()
        os.environ.update(saved)
