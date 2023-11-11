from xmlrpc.client import Boolean
from pydantic import BaseModel
class CollectionName:

    UsersBase='goapp_users'
    UsersRoles='goapp_user_Roles'
    UserPermissions='goapp_user_permissions'

    UserAssignedRole='goapp_user_assigned_role'
    UserAssignedAdditionalPermission='goapp_user_assigned_additional_permission'
    
    RolesAssociatedWithPermissions='goapp_role_assigned_permissions'

def WrapperNone(args):
    return '' if args is None else args

class UsersBase(BaseModel):
    user_slug:str
    first_name:str
    last_name:str
    email:str
    date_created:int
    is_active:Boolean = True
    is_deleted:Boolean = False

class UserWithPassword(UsersBase):
    password:str

class UserAssignedRole(BaseModel):
    uar_slug:str
    user_role_slug:str
    date_assigned:str
    is_active:Boolean

class UserAssignedAdditionalPermission(BaseModel):
    uaar_slug:str
    user_perm_slug:str
    date_assigned:str
    is_active:Boolean

class UserRoles(BaseModel):
    role_slug:str
    is_active:Boolean
    role_name:str

class UserPermissions(BaseModel):
    perm_slug:str
    is_active:Boolean
    perm_name:str

class RolesAssociatedWithPermissions(BaseModel):
    rawp_slug:str
    role_slug:str
    perm_slug:str
    is_active:Boolean