import time

from gpmappy.client import GpmapClient


def main() -> None:
    client = GpmapClient()
    variants = [5553693, 5553694]

    start = time.time()
    try:
        client.variants(variants, expand=False)
    except Exception:
        pass
    no_expand = time.time() - start

    start = time.time()
    try:
        client.variants(variants, expand=True)
    except Exception:
        pass
    expand = time.time() - start

    print(f"expand_false={no_expand:.4f}s expand_true={expand:.4f}s")


if __name__ == "__main__":
    main()
