from fastapi import APIRouter

from app.api.routes import ai, analytics, audit, auth, crm, feedback, pathologies, reports, studies, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(studies.router)
api_router.include_router(ai.router)
api_router.include_router(reports.router)
api_router.include_router(crm.router)
api_router.include_router(pathologies.router)
api_router.include_router(feedback.router)
api_router.include_router(audit.router)
api_router.include_router(analytics.router)
