from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.state import limiter

# slowapi limiter lives in app.state; registered here so its middleware/handlers find it.
app = FastAPI(title="Notepad API")
app.state.limiter = limiter
# Register slowapi 429 handler + middleware so @limiter.limit returns HTTP 429 (T-04-01 /login throttle).
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Conditional CORS: empty => same-origin (no middleware); split-domain sets explicit origins, never "*" (refresh cookie needs allow_credentials).
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


# Routers imported after `app` is defined; they import `limiter` from app.state to avoid a circular import.
from app.routers import auth, notes  # noqa: E402

app.include_router(auth.router)
app.include_router(notes.router)
