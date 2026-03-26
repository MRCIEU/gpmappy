from gpmappy import __all__


def test_expected_exports_present() -> None:
    expected = {
        "GpmapClient",
        "all_genes",
        "all_traits",
        "associations",
        "gene",
        "genes",
        "get_all_gene_pleiotropies",
        "get_all_snp_pleiotropies",
        "get_gwas",
        "health_api",
        "ld_matrix",
        "ld_proxies",
        "region",
        "search_gpmap",
        "select_api",
        "trait",
        "traits",
        "upload_gwas",
        "variant",
        "variants",
        "version_api",
    }
    assert expected.issubset(set(__all__))
