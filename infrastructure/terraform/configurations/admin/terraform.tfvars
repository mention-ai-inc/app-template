preferred_region = "us-east-1"
github_repo      = "mention-ai-inc/app-template"
domain_name      = "acme.example.com"
admin_subdomain  = "admin"
python_warnings  = "ignore::DeprecationWarning:authlib\\._joserfc_helpers"

oidc_issuer                 = "https://clerk.acme.example.com"
oidc_authorization_endpoint = "https://clerk.acme.example.com/oauth/authorize"
oidc_token_endpoint         = "https://clerk.acme.example.com/oauth/token"
oidc_user_info_endpoint     = "https://clerk.acme.example.com/oauth/userinfo"
oidc_scope                  = "openid email profile"

rate_limit_per_five_minutes = 600
