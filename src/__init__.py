from fastapi import FastAPI
import os
import logging

app = FastAPI()

# setup logging
logging.config.fileConfig('src/config/logging.conf', disable_existing_loggers=False)
logger = logging.getLogger(__name__) 


def flush_print(*args, **kwargs):
    print("*"*25)
    print(*args, **kwargs, flush=True)
    print("*"*25)


def create_app():

    #import all routers
    from src.apis import apis
    
    #Register all routers
    app.include_router(apis)
    
    return app


@app.get("/ping")
def ping():
    return {
        "version": "1.0.0"
    }