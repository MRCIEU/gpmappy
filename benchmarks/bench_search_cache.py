import time

from gpmappy.client import GpmapClient


def main() -> None:
    client = GpmapClient()
    start = time.time()
    try:
        client.search_gpmap("haemoglobin")
    except Exception:
        pass
    first = time.time() - start

    start = time.time()
    try:
        client.search_gpmap("haemoglobin")
    except Exception:
        pass
    second = time.time() - start

    print(f"first={first:.4f}s second={second:.4f}s")


if __name__ == "__main__":
    main()
