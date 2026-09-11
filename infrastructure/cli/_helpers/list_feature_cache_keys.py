import os

import redis

OUTPUT_PATH = "redis-keys.txt"
REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PASSWORD = os.environ["REDIS_PASSWORD"]


def list_keys() -> None:
    connection_pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=6379,
        db=0,
        decode_responses=True,
        password=REDIS_PASSWORD,
    )
    r = redis.Redis(connection_pool=connection_pool)
    cursor = 0
    all_keys: list[str] = []
    while True:
        cursor, keys = r.scan(cursor=cursor, count=500)
        all_keys.extend(keys)
        if cursor == 0:
            break
    all_keys.sort()
    with open(OUTPUT_PATH, "w") as f:
        for key in all_keys:
            f.write(key + "\n")
    print(f"Wrote {len(all_keys)} keys from Redis ({REDIS_HOST}) to {OUTPUT_PATH}")


def main() -> None:
    list_keys()


if __name__ == "__main__":
    main()
