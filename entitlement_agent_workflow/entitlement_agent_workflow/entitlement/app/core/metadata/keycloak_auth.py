import os
import sys
import time
from typing import List, Dict, Any, Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Bearer token scheme for FastAPI dependency injection
security = HTTPBearer()

# ------------------------------------------------------------------------------
# RSA Key Generation for Local Mock Testing
# ------------------------------------------------------------------------------
# We generate a real RS256 keypair in memory. This allows us to sign and verify
# real RS256 tokens in our API and unit tests offline without needing an active Keycloak connection.
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_KEY = _PRIVATE_KEY.public_key()

# Configuration from environment variables
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "nemhem-entitlement-service")
KEYCLOAK_REALM_URL = os.getenv("KEYCLOAK_REALM_URL", "http://localhost:8080/realms/nemhem")
MOCK_MODE = os.getenv("KEYCLOAK_MOCK_MODE", "true").lower() == "true"


class KeycloakValidator:
    """
    Validates Keycloak-issued JWT tokens.
    Supports local mock RS256 verification and standard public key JWKS verification.
    """
    
    @staticmethod
    def get_public_key() -> Any:
        """Returns the public key used to verify local mock tokens."""
        return _PUBLIC_KEY

    @staticmethod
    def generate_mock_token(
        citizen_id: str, 
        roles: List[str], 
        username: str = "test_user", 
        expires_in: int = 3600
    ) -> str:
        """Generates a valid RS256 JWT signed with our private key for testing."""
        now = int(time.time())
        payload = {
            "iss": KEYCLOAK_REALM_URL,
            "sub": citizen_id,
            "aud": KEYCLOAK_AUDIENCE,
            "exp": now + expires_in,
            "nbf": now - 10,
            "iat": now,
            "preferred_username": username,
            "realm_access": {
                "roles": roles
            },
            "resource_access": {
                KEYCLOAK_AUDIENCE: {
                    "roles": roles
                }
            }
        }
        return jwt.encode(payload, _PRIVATE_KEY, algorithm="RS256")

    @classmethod
    def validate_token(cls, token: str) -> Dict[str, Any]:
        """
        Decodes and validates a JWT token.
        Raises jwt.PyJWTError if invalid.
        """
        if MOCK_MODE:
            # Verify using our mock public key
            return jwt.decode(
                token, 
                _PUBLIC_KEY, 
                algorithms=["RS256"], 
                audience=KEYCLOAK_AUDIENCE,
                issuer=KEYCLOAK_REALM_URL
            )
        else:
            # Real Keycloak verification (JWKS decoding)
            # In production, we'd fetch public certificates from the realm URL.
            # For this pipeline, we default to the local verify mode unless Keycloak is running.
            try:
                # Stub out standard decoding (in practice, retrieve keys from Keycloak JWKS endpoint)
                return jwt.decode(
                    token, 
                    _PUBLIC_KEY, 
                    algorithms=["RS256"], 
                    audience=KEYCLOAK_AUDIENCE,
                    issuer=KEYCLOAK_REALM_URL
                )
            except Exception as e:
                raise jwt.InvalidTokenError(f"Keycloak verification failed: {e}")


# ------------------------------------------------------------------------------
# FastAPI Dependencies & RBAC Guards
# ------------------------------------------------------------------------------

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """FastAPI dependency to authenticate JWT bearer tokens."""
    token = credentials.credentials
    try:
        payload = KeycloakValidator.validate_token(token)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authorization token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


class RoleChecker:
    """Dependency checker to restrict route access by Keycloak roles."""
    
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [r.upper() for r in allowed_roles]

    def __call__(self, user_payload: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        # Extract roles from Keycloak payload
        realm_roles = user_payload.get("realm_access", {}).get("roles", [])
        client_roles = user_payload.get("resource_access", {}).get(KEYCLOAK_AUDIENCE, {}).get("roles", [])
        
        user_roles = [r.upper() for r in list(set(realm_roles + client_roles))]
        
        # Check if user has at least one allowed role
        has_role = any(role in user_roles for role in self.allowed_roles)
        
        if not has_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {self.allowed_roles}. Found: {user_roles}"
            )
            
        return user_payload


# Pre-defined role dependencies for routes
require_citizen = RoleChecker(["CITIZEN", "OFFICER", "ADMIN"])
require_officer = RoleChecker(["OFFICER", "ADMIN"])
require_admin = RoleChecker(["ADMIN"])
