from fastapi import APIRouter, Cookie, Response, Request
from fastapi import FastAPI, Depends, HTTPException
from src.models.db_schema import CollectionName, UsersBase
from src.config.database import db, c_name, SingleDataReader
import traceback, sys
from src.models.api_schemas import TokenRefreshed, UserSignIn, UserTokenInfo, UserSignOut
from datetime import datetime, timedelta
from src.utils.auth import check_jwt_expiration, create_tokens, decode_token, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES
from src.utils.permissions import TokenRequired

router = APIRouter(prefix="/auth")


@router.post("/login", tags=["auth"])
async def auth_login(userSignIn: UserSignIn, response: Response):
    try:
        user:UsersBase = None
        if userSignIn.email and userSignIn.password:
            user = SingleDataReader(c_name.UsersBase, {"email": userSignIn.email, "password": userSignIn.password}, None)
        elif userSignIn.api_token:
            user = db[c_name.UsersBase].find_one({"email": userSignIn.email, "api_token": userSignIn.api_token})
        
        if user is not None:
            payload = {"sub":user['user_slug'], "role":"OrgAdmin"}
            access_token, refresh_token, _ = create_tokens(payload=payload)
            user_data = UserTokenInfo(
                token= dict(
                    access_token= access_token,
                    refresh_token= refresh_token
                ),
                permission= [1, 2],
                role= "Org Admin",
                unique= user['user_slug']
            )
            response.set_cookie(key="access_token", value=access_token, secure=True, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
            response.set_cookie(key="refresh_token", value=refresh_token, secure=True, httponly=True, max_age=REFRESH_TOKEN_EXPIRE_MINUTES * 60)
            return user_data

        raise HTTPException(status_code=400, detail="Authentication failed")
    except Exception as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", e)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()


@router.post("/logout", tags=["auth"], dependencies=[Depends(TokenRequired)])
async def auth_logout(response: Response):
    try:
        response.delete_cookie(key="access_token", path="/", domain=None, secure=True, httponly=True)
        response.delete_cookie(key="refresh_token", path="/", domain=None, secure=True, httponly=True)

        return UserSignOut(message= "Logged out successfully")
    except Exception as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", e)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()


@router.post("/verify", tags=["auth"], dependencies=[Depends(TokenRequired)])
async def auth_verify(request: Request, response: Response):
    try:

        cookies = request.cookies

        refresh_token = cookies.get("refresh_token")
        decoded_token = decode_token(refresh_token)

        if decoded_token and decoded_token.get("type") == "refresh":

            access_token, refresh_token = None, None
            token_refreshed = False

            #Refresh both the token if refresh token is about to expire in 5 mins
            if check_jwt_expiration(decoded_token, 5):
                access_token, refresh_token, _ = create_tokens(decoded_token)

                response.delete_cookie(key="access_token", path="/", domain=None, secure=True, httponly=True)
                response.delete_cookie(key="refresh_token", path="/", domain=None, secure=True, httponly=True)
                response.set_cookie(key="access_token", value=access_token, secure=True, httponly=True)
                response.set_cookie(key="refresh_token", value=refresh_token, secure=True, httponly=True)
                message = "Tokens refreshed!!!"
                token_refreshed = True
            
            #Refresh only access token if its about to expire in 30 mins
            else:
                if check_jwt_expiration(decoded_token, 30):
                    access_token, _, _ = create_tokens(decoded_token)

                    response.delete_cookie(key="access_token", path="/", domain=None, secure=True, httponly=True)
                    response.set_cookie(key="access_token", value=access_token, secure=True, httponly=True)
                    message = "Access refreshed!!!"
                    token_refreshed = True
                else:
                    message = "User authorized!!!"

            return {"message": message, "access_token": access_token, "refresh_token": refresh_token, "token_refreshed":token_refreshed}

        else:
            raise HTTPException(status_code=401, detail="Unauthorized login!!!")
    except Exception as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", e)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()