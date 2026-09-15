import os
from typing import cast

import google.auth
import redis
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from library_provider_gcp.cloud.constants import FEATURE_PROJECT_ID

feature_environment = os.environ["FEATURE_ENVIRONMENT"]


def get_redis_ip() -> str:
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials = cast(Credentials, credentials)
    credentials.refresh(Request())
    auth_token = credentials.token
    instance_name = f"{feature_environment}cache"
    url = f"https://compute.googleapis.com/compute/v1/projects/{FEATURE_PROJECT_ID}/aggregated/instances"
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    response = requests.get(url, headers=headers, params={"filter": f'name = "{instance_name}"'})
    try:
        for zone_payload in response.json().get("items", {}).values():
            for instance in zone_payload.get("instances", []):
                return instance["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
        raise KeyError(f"Instance '{instance_name}' not found")
    except Exception:
        print(response.text)
        raise


def clear_cache(*, redis_ip: str, redis_password: str) -> None:
    connection_pool = redis.ConnectionPool(
        host=redis_ip,
        port=6379,
        db=0,
        decode_responses=False,
        password=redis_password,
    )
    r = redis.Redis(connection_pool=connection_pool)
    r.flushall()
    print("Redis cache cleared")


def main() -> None:
    redis_ip = get_redis_ip()
    clear_cache(redis_ip=redis_ip, redis_password=os.environ["REDIS_PASSWORD"])


if __name__ == "__main__":
    main()
