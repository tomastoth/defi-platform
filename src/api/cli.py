from src.api.core.logger import logger
from src.api.factory import create_app

app = create_app()

if __name__ == '__main__':
    import uvicorn

    logger.info("Starting uvicorn in reload mode")
    uvicorn.run(
        "cli:app",
        host="0.0.0.0",
        reload=True,
        port=int("8001"),
    )
