from gpmappy import gene, genes


def main() -> None:
    single = gene("WNT7B")
    print(single.keys())
    print(type(single["coloc_groups"]).__name__)

    multi = genes(["WNT7B", "WNT7A"], as_dataframe=False)
    print(multi.keys())
    print(type(multi["genes"]).__name__)


if __name__ == "__main__":
    main()
