from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# slowapi limiter on app.state; the /login rate-limit decorator is applied in Plan 04.
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Notepad API")
app.state.limiter = limiter

# Conditional CORS (Open Question 1 resolution):
#   - Prod default is SAME-ORIGIN behind a reverse proxy => CORS_ORIGINS empty => no middleware.
#   - Split-domain deploys set CORS_ORIGINS to explicit origins; never "*" with credentials,
#     because the refresh cookie requires allow_credentials=True.
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
        allow_credentials=True,  # required for refresh cookie cross-origin
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# Router includes added by later plans:
#   from app.routers import auth, notes
#   app.include_router(auth.router); app.include_router(notes.router)
