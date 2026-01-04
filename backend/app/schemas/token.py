from pydantic import BaseModel


class TokenResponse(BaseModel):
    """Access-token response body. The refresh token rides in an httpOnly cookie."""

    access_token: str
    token_type: str = "bearer"
