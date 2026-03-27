import time
from contextlib import suppress

from gpmappy.client import GpmapClient


def main() -> None:
    client = GpmapClient()
    variants = [5553693, 5553694]

    start = time.time()
    with suppress(Exception):
        client.variants(variants, expand=False)
    no_expand = time.time() - start

    start = time.time()
    with suppress(Exception):
        client.variants(variants, expand=True)
    expand = time.time() - start

    print(f"expand_false={no_expand:.4f}s expand_true={expand:.4f}s")


if __name__ == "__main__":
    main()
