from urllib.request import Request
from fastapi import APIRouter, Depends
from src.utils.permissions import TokenRequired, SuperAdminAccess, OrgStaffAccess
import traceback, sys

router = APIRouter(prefix="/users", dependencies=[Depends(TokenRequired)])

@router.post("/get-users", tags=["Add User"], dependencies=[Depends(OrgStaffAccess)])
async def get_user():
    try:
        return{
            "msg": "Only accessible to Super Admin & Org Admin",
            "success":True
        }
    except Exception as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", e)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()

@router.post("/add-user", tags=["Add User"], dependencies=[Depends(SuperAdminAccess)])
async def add_user():
    try:
        return{
            "msg": "Only accessible to Super Admin",
            "success":True
        }
    except Exception as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", e)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()

@router.put("/update-user")
async def update_user():
    try:
        pass
    except Exception as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", e)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()

@router.post("/delete-user")
async def delete_user():
    try:
        pass
    except Exception as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", e)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()