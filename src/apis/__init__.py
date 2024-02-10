from fastapi import APIRouter


#Import all routers
from src.apis.authentication import router as auth_router
from src.apis.account import router as accountRouter
from src.apis.clients import router as clientRouter
from src.apis.currency import router as currencyRouter
from src.apis.invoice import router as invoiceRouter
from src.apis.organization import router as organizationRouter
from src.apis.transactions import router as transactionRouter
from src.apis.users import router as usersRouterRouter
from src.apis.work_orders import router as workOrderRouter

apis = APIRouter()


#Register all routers
apis.include_router(auth_router)
apis.include_router(accountRouter)
apis.include_router(clientRouter)
apis.include_router(currencyRouter)
apis.include_router(invoiceRouter)
apis.include_router(organizationRouter)
apis.include_router(transactionRouter)
apis.include_router(usersRouterRouter)
apis.include_router(workOrderRouter)


__all__ = ["apis"]