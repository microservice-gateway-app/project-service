from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from injector import Binder
from pydantic_settings import BaseSettings


class ProjectServiceConfigurations(BaseSettings):
    DB_URI: str = "postgresql+asyncpg://projects:projects@localhost:54320/projects"
    SECRET_KEY: str = "project-service-secret"
    ALGORITHM: str = "HS256"
    PRIVATE_KEYFILE: str = "private.pem"

    @property
    def private_key(self) -> RSAPrivateKey:
        with open(self.PRIVATE_KEYFILE, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=self.SECRET_KEY.encode(),
                backend=default_backend(),
            )
        if not isinstance(private_key, RSAPrivateKey):
            raise TypeError(
                f"Expected RSAPrivateKey, but got {type(private_key).__name__}"
            )

        return private_key


def provide_config(binder: Binder):
    binder.bind(ProjectServiceConfigurations)
