import uvicorn
from fastapi import FastAPI

from projects.module import provide_injector


injector = provide_injector()
app = injector.get(FastAPI)

if __name__ == "__main__":
    uvicorn.run(app)
