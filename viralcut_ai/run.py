import os
import sys
import uvicorn

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from backend.config import settings  # noqa: E402


if __name__ == "__main__":
    print(f"\nLaunching {settings.PROJECT_NAME} v{settings.VERSION} at http://localhost:{settings.PORT} ...\n")
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        app_dir=PROJECT_DIR,
    )
