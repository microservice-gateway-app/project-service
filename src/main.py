import logging

import uvicorn
from fastapi import FastAPI

from projects.module import provide_injector

logging.basicConfig(
    format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

injector = provide_injector()
app = injector.get(FastAPI)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
