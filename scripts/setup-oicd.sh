# Example setup for OIDC with Zitadel
export LD_ENABLE_OIDC=True
export OIDC_USE_PKCE=True
export OIDC_OP_AUTHORIZATION_ENDPOINT=http://localhost:8080/oauth/v2/authorize
export OIDC_OP_TOKEN_ENDPOINT=http://localhost:8080/oauth/v2/token
export OIDC_OP_USER_ENDPOINT=http://localhost:8080/oidc/v1/userinfo
export OIDC_OP_JWKS_ENDPOINT=http://localhost:8080/oauth/v2/keys
export OIDC_RP_CLIENT_ID=<client-id>
