from base64 import b64decode
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi import Body, Header, HTTPException
from jose import jwt
from pydantic import BaseModel, Field, field_validator

from ..config import ProjectServiceConfigurations
from ..controllers.base import BaseController, controller
from ..core.services.access import ProjectScope


class AccessTokenRequest(BaseModel):
    scopes: list[ProjectScope] = Field(default_factory=list, min_length=1)

    @field_validator("scopes", mode="before")
    def validate_scopes(cls, value: list[str]):
        return [
            ProjectScope(scope)
            for scope in list[str](value)
            if scope in ProjectScope._value2member_map_
        ]

    ttl: int = Field(default=1200, description="Access token time-to-live", le=2400)


class AccessTokenResponse(BaseModel):
    access_token: str


@controller
class AccessController(BaseController):
    def __init__(self, config: ProjectServiceConfigurations) -> None:
        super().__init__(prefix="/tokens")
        self.config = config

    def init_routes(self) -> None:
        self.router.post("")(self.create_access_token)

    def get_actor_id_from_header(self, header_value: str) -> str:
        private_key = self.config.private_key
        encrypted_from_client = b64decode(header_value.encode())
        decrypted = private_key.decrypt(
            encrypted_from_client,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return decrypted.decode()

    def create_access_token(
        self,
        request_body: Annotated[AccessTokenRequest, Body()],
        encrypted_actor_id: str = Header(alias="X-Actor-ID"),
    ) -> AccessTokenResponse:
        actor_id = self.get_actor_id_from_header(encrypted_actor_id)
        # Validate scopes
        scopes = request_body.scopes
        if not scopes:
            raise HTTPException(status_code=400, detail="Scopes must not be empty")

        # Generate the JWT
        ttl = request_body.ttl
        now = datetime.now(UTC)
        exp = now + timedelta(seconds=ttl)
        payload: dict[str, Any] = {
            "sub": actor_id,
            "scopes": [s.value for s in scopes],
            "iat": now,
            "exp": exp,
        }
        access_token = jwt.encode(
            payload,
            key=self.config.SECRET_KEY,
            algorithm=self.config.ALGORITHM,
        )

        # Return the access token
        return AccessTokenResponse(access_token=access_token)
