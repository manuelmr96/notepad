from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.state import limiter

# slowapi limiter lives in app.state module; routers import it from there. It is
# also registered on app.state below so slowapi's middleware/handlers find it.
app = FastAPI(title="Notepad API")
app.state.limiter = limiter
# Register slowapi's 429 handler + middleware so @limiter.limit decorators
# actually return HTTP 429 (rather than raising 500) when a limit is exceeded
# (T-04-01: /login brute-force throttle).
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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


# Routers (imported after `app` is defined; routers import `limiter` from
# app.state, so there is no circular import with this module).
from app.routers import auth  # noqa: E402

app.include_router(auth.router)

# Further router includes added by later plans:
#   from app.routers import notes
#   app.include_router(notes.router)
