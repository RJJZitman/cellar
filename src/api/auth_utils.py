from typing import Optional

from fastapi import HTTPException, Request
from fastapi.security import OAuth2
from fastapi.security.base import SecurityBase
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from starlette.status import HTTP_403_FORBIDDEN


class BasicAuth(SecurityBase):
    """
    Basic auth model for swagger UI access.
    """
    def __init__(self, scheme_name: str = None, auto_error: bool = True):
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error
        self.model = SecurityBase()

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "basic":
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
                )
            else:
                return None
        return param


class OAuth2PasswordBearerCookie(OAuth2):
    """
    Oath2 Cookie bearer. Enables view access to the swagger UI when accessing the /login page.
    """
    def __init__(self, token_url: str, scheme_name: str = None, scopes: dict = None, auto_error: bool = True):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": token_url, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        """
        Places either the cookie or header scheme.
        """
        header_authorization: str = request.headers.get("Authorization")
        cookie_authorization: str = request.cookies.get("Authorization")

        header_scheme, header_param = get_authorization_scheme_param(header_authorization)
        cookie_scheme, cookie_param = get_authorization_scheme_param(cookie_authorization)

        # authorization = True
        if header_scheme.lower() == "bearer":
            return header_param
        elif cookie_scheme.lower() == "bearer":
            return cookie_param
        else:
            if self.auto_error:
                raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Not authenticated")
            else:
                return None
