from gpmappy import search_gpmap


def main() -> None:
    print(search_gpmap("haemoglobin").head())


if __name__ == "__main__":
    main()
