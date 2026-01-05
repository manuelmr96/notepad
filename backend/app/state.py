"""Shared application-level singletons that routers and the app entrypoint both
need, kept here to avoid a circular import between ``app.main`` and routers.

The slowapi ``Limiter`` lives here so route modules can apply
``@limiter.limit(...)`` decorators (e.g. the /login throttle, T-04-01) without
importing ``app.main`` (which imports the routers).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
