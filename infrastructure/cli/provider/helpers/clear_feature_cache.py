import os

from cache_client import REDIS_HOST, tls_client

feature_environment = os.environ["FEATURE_ENVIRONMENT"]


def clear_cache() -> None:
    if not feature_environment:
        raise SystemExit("Refusing to flush a cache without a feature environment prefix")

    tls_client(decode_responses=False).flushall()
    print(f"Flushed {REDIS_HOST} for feature environment {feature_environment}")


def main() -> None:
    clear_cache()


if __name__ == "__main__":
    main()
