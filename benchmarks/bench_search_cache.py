import time
from contextlib import suppress

from gpmappy.client import GpmapClient


def main() -> None:
    client = GpmapClient()
    start = time.time()
    with suppress(Exception):
        client.search_gpmap("haemoglobin")
    first = time.time() - start

    start = time.time()
    with suppress(Exception):
        client.search_gpmap("haemoglobin")
    second = time.time() - start

    print(f"first={first:.4f}s second={second:.4f}s")


if __name__ == "__main__":
    main()
