from gpmappy import gene, genes


def main() -> None:
    print(gene("WNT7B").keys())
    print(genes(["WNT7B", "WNT7A"]).keys())


if __name__ == "__main__":
    main()
