from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.utils.auth import check_jwt_expiration
from src.utils.auth import create_tokens, decode_token
from src.utils.permissions import JWTRequired

app = FastAPI(version='0.78.0')


# setup logging
# logging.config.fileConfig('src/config/logging.conf', disable_existing_loggers=False)


def flush_print(*args, **kwargs):
    print("*" * 25)
    print(*args, **kwargs, flush=True)
    print("*" * 25)


def create_app():
    # import all routers
    from src.apis import apis

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Register all routers
    app.include_router(apis, prefix="/apis")

    app.add_middleware(
        CORSMiddleware,
        allow_origins="*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/static", StaticFiles(directory="src/static"), name="static")

    return app


@app.middleware("http")
def after_request(request: Request, call_next):
    response = call_next(request)
    return response


# @app.middleware("http", dependencies=[Depends(JWTRequired)])
# def auth_verify(request: Request, call_next):
#     try:
#
#         cookies = request.cookies
#
#         refresh_token = cookies.get("refresh_token")
#         decoded_token = decode_token(refresh_token)
#
#         response = call_next(request)
#
#         if decoded_token and decoded_token.get("type") == "refresh":
#
#             access_token, refresh_token = None, None
#
#             # Refresh both the token if refresh token is about to expire in 5 mins
#             if check_jwt_expiration(decoded_token, 5):
#                 access_token, refresh_token, _ = create_tokens(decoded_token)
#
#                 response.delete_cookie(key="access_token", path="/", domain=None, secure=True, httponly=True)
#                 response.delete_cookie(key="refresh_token", path="/", domain=None, secure=True, httponly=True)
#                 response.set_cookie(key="access_token", value=access_token, secure=True, httponly=True)
#                 response.set_cookie(key="refresh_token", value=refresh_token, secure=True, httponly=True)
#                 message = "Tokens refreshed!!!"
#
#             # Refresh only access token if its about to expire in 30 mins
#             else:
#                 if check_jwt_expiration(decoded_token, 30):
#                     access_token, _, _ = create_tokens(decoded_token)
#
#                     response.delete_cookie(key="access_token", path="/", domain=None, secure=True, httponly=True)
#                     response.set_cookie(key="access_token", value=access_token, secure=True, httponly=True)
#
#             return response
#
#         else:
#             respone: Response = None
#             response.delete_cookie(key="access_token", path="/", domain=None, secure=True, httponly=True)
#             response.delete_cookie(key="refresh_token", path="/", domain=None, secure=True, httponly=True)
#
#             raise HTTPException(status_code=401, detail=respone)
#     except Exception as e:
#         ex_type, ex_value, ex_traceback = sys.exc_info()
#         print("Exception : ", e)
#         print("Exception type : ", ex_type.__name__)
#         print("Exception message : ", ex_value)
#         traceback.print_exc()


@app.get("/ping")
def ping():
    return {
        "version": "1.0.0"
    }
