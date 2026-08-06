from pydantic import BaseModel


class TokenResponse(BaseModel):
    """
    Response returned after successful authentication.

    The client sends access_token with future protected requests.
    """

    access_token: str
    token_type: str = "bearer"
    