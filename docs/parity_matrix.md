# gpmappy Parity Matrix

Tracks gpmapr 0.0.2.0. `tests/contract/test_parity_contract.py` enforces this table: every
gpmapr export must exist with the same parameters, and the scenarios in
`tests/contract/scenarios.json` must produce the same requests and outputs (see
[Parity contract](api_contract.md#parity-contract-with-gpmapr)).

## Legend

- Status: `todo` | `in_progress` | `done` | `intentional_divergence`
- Return Policy: `dict`, `dataframe`, `dict+dataframe`, `raw`

| R Function | Python Surface | Raw API Method(s) | Endpoint(s) | Input Validation Rules | Transform/Business Logic | Expected Return Shape | Test Cases Required | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| select_api | `GpmapClient.select_api` | n/a | n/a | api in {dev, production} | set base URL | None | valid and invalid env | intentional_divergence | internal in gpmapr; exported by gpmappy |
| health_api | `GpmapClient.health_api` | `health_api` | `/health` | none | none | dict | healthy and unhealthy, HTTP errors | done | |
| version_api | `GpmapClient.version_api` | `version_api` | `/v1/info/version` | none | extract `version` key | str | key exists and missing key | intentional_divergence | internal in gpmapr, which also refuses to load on an API version mismatch; gpmappy does not check on import |
| search_gpmap | `GpmapClient.search_gpmap` | `search_options_api`, `search_variants_api` | `/v1/search/options`, `/v1/search/variant/{query}` | non-empty search_text, rsquared in [0, 1] | cached options, variant branch for `rs...` / `chr:bp`, call column, ordered by coloc groups + rare results with the searched variant first | dataframe | trait text search, rs query, empty result, ordering | done | gpmapr also fetches search options for variant searches, and gives every proxy the first proxy's `num_coloc_studies` |
| all_traits | `GpmapClient.all_traits` | `traits_api` | `/v1/traits` | none | extract `traits` | dataframe | non-empty and empty payload | done | |
| trait_duplicates | `GpmapClient.trait_duplicates` | `trait_duplicates_api` | `/v1/traits/duplicates` | none | extract `duplicates` | dataframe | duplicate-group shape | done | |
| trait | `GpmapClient.trait` | `trait_api`, `trait_coloc_pairs_api`, `trait_associations_full_api`, `get_gwas_api` | `/v1/traits/{id}`, `/v1/traits/{id}/coloc-pairs`, `/v1/traits/{id}/associations-full`, `/v1/gwas/{guid}` | trait_id required | GUID branch with upload association merge, merge associations, coloc pairs and full associations as tables, source_url | dict+dataframe | guid and non-guid, coloc and full-association toggles | done | |
| traits | `GpmapClient.traits` | `specific_traits_api`, `trait_coloc_pairs_api`, `get_gwas_api` | `/v1/traits?...` + coloc endpoint + gwas endpoint | max 10 ids, no missing ids | split guid/non-guid, merge upload results, de-duplicated coloc pairs | dict+dataframe | mixed IDs, include_associations and include_coloc_pairs | done | |
| all_genes | `GpmapClient.all_genes` | `genes_api` | `/v1/genes` | none | extract `genes` | dataframe | non-empty and empty payload | done | |
| gene | `GpmapClient.gene` | `gene_api` | `/v1/genes/{id}` | gene_id required | cleanup + optional association merge | dict+dataframe | include flags behavior | done | |
| genes | `GpmapClient.genes` | `specific_genes_api` | `/v1/genes?...` | max 10 ids, no missing ids | dedupe ids + optional association merge | dict+dataframe | limit and empty and flags | done | |
| variant | `GpmapClient.variant` | `variant_api`, `variant_summary_stats_api` | `/v1/variants/{id}`, `/v1/variants/{id}/summary-stats` | variant_id required | optional summary stats, merge associations | dict+dataframe | summary-stats extraction | done | |
| variants | `GpmapClient.variants` | `variants_api` | `/v1/variants?...` | max 10 expand, max 50 non-expand | dedupe + optional association merge | dict+dataframe | expand and non-expand limits | done | |
| region | `GpmapClient.region` | `region_api` | `/v1/regions/{id}` | region_id required | cleanup + optional association merge | dict+dataframe | include flags behavior | done | gpmapr errors when `include_associations=TRUE` and the API sends no associations; gpmappy returns the region |
| ld_matrix | `GpmapClient.ld_matrix` | `ld_matrix_by_variant_api`, `ld_matrix_by_variant_id_api` | `/v1/ld/matrix?...` | variant_ids required | numeric vs string branch | dict/dataframe | variant_id and rsid paths | done | |
| ld_proxies | `GpmapClient.ld_proxies` | `ld_proxies_by_variant_api`, `ld_proxies_by_variant_id_api` | `/v1/ld/proxies?...` | variant_ids required | numeric vs string branch | dict/dataframe | variant_id and rsid paths | done | |
| associations | `GpmapClient.associations` | `associations_api` | `/v1/associations?...` | variant_ids and study_ids required | extract `associations` | dataframe | id filtering and empty response | done | |
| get_all_gene_pleiotropies | `GpmapClient.get_all_gene_pleiotropies` | `gene_pleiotropies_api` | `/v1/pleiotropy/genes` | none | extract `genes` | dataframe | non-empty and empty payload | done | |
| get_all_variant_pleiotropies | `GpmapClient.get_all_variant_pleiotropies` | `variant_pleiotropies_api` | `/v1/pleiotropy/snps` | none | extract `snps` | dataframe | non-empty and empty payload | done | `get_all_snp_pleiotropies` remains as a deprecated alias |
| get_gwas | `GpmapClient.get_gwas` | `get_gwas_api`, `get_gwas_summary_stats_api` | `/v1/gwas/{id}`, `/v1/gwas/{id}/summary-stats` | gwas_id required | optional associations and summary stats | dict+dataframe | with and without summary stats | done | |
| upload_gwas | `GpmapClient.upload_gwas` | `upload_gwas_api` | `/v1/gwas` | file exists,<1GB; category/ancestry/reference_build; thresholds; `*_col` arguments; columns present in file header; comparison GUIDs | multipart upload + JSON request; deprecated `column_names` mapped to API names | dict | validation failures + success | done | |
| delete_gwas | `GpmapClient.delete_gwas` | `delete_gwas_api` | `DELETE /v1/gwas/{guid}` | GUID and non-blank email | JSON body with email; API errors re-raised with the detail | dict | validation, success, not found | done | |
