from gpmappy import trait, traits


def main() -> None:
    print(trait(5020).keys())
    print(traits([4405, 4872]).keys())


if __name__ == "__main__":
    main()
