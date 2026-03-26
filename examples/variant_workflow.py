from gpmappy import variant, variants


def main() -> None:
    print(variant(5553693).keys())
    print(variants([5553693, 5553694], expand=False).keys())


if __name__ == "__main__":
    main()
