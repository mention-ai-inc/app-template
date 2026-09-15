from cache_client import REDIS_HOST, tls_client

OUTPUT_PATH = "redis-keys.txt"


def list_keys() -> None:
    client = tls_client(decode_responses=True)
    cursor = 0
    all_keys: list[str] = []
    while True:
        cursor, keys = client.scan(cursor=cursor, count=500)
        all_keys.extend(keys)
        if cursor == 0:
            break
    all_keys.sort()
    with open(OUTPUT_PATH, "w") as output:
        for key in all_keys:
            output.write(key + "\n")
    print(f"Wrote {len(all_keys)} keys from Azure Cache for Redis ({REDIS_HOST}) to {OUTPUT_PATH}")


def main() -> None:
    list_keys()


if __name__ == "__main__":
    main()
