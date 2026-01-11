"""Shared app singletons (slowapi ``Limiter``) kept here to avoid a circular import between ``app.main`` and routers."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
