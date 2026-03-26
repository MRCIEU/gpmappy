# gpmappy Phase 1 Parity Matrix

## Legend

- Status: `todo` | `in_progress` | `done` | `intentional_divergence`
- Return Policy: `dict`, `dataframe`, `dict+dataframe`, `raw`

| R Function | Python Surface | Raw API Method(s) | Endpoint(s) | Input Validation Rules | Transform/Business Logic | Expected Return Shape | Test Cases Required | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| select_api | `GpmapClient.select_api` | n/a | n/a | api in {dev, production, custom} | set base URL | None | valid and invalid env | done | custom accepts full URL |
| health_api | `GpmapClient.health_api` | `health_api` | `/health` | none | none | dict | healthy and unhealthy, HTTP errors | done | |
| version_api | `GpmapClient.version_api` | `version_api` | `/v1/info/version` | none | extract `version` key | str | key exists and missing key | done | |
| search_gpmap | `GpmapClient.search_gpmap` | `search_options_api`, `search_variants_api` | `/v1/search/options`, `/v1/search/variant/{query}` | non-empty search_text, rsquared in [0, 1] | cached options, variant-path branching, call-column generation | dataframe | trait text search, rs query, empty result | done | cache is in-memory TTL |
| all_traits | `GpmapClient.all_traits` | `traits_api` | `/v1/traits` | none | extract `traits` | dataframe | non-empty and empty payload | done | |
| trait | `GpmapClient.trait` | `trait_api`, `trait_coloc_pairs_api`, `get_gwas_api` | `/v1/traits/{id}`, `/v1/traits/{id}/coloc-pairs`, `/v1/gwas/{guid}` | trait_id required | GUID branch, merge associations, source_url | dict+dataframe | guid and non-guid, coloc toggles | done | |
| traits | `GpmapClient.traits` | `specific_traits_api`, `trait_coloc_pairs_api`, `get_gwas_api` | `/v1/traits?...` + coloc endpoint + gwas endpoint | max 10 ids, no nulls | split guid/non-guid, merge upload results | dict+dataframe | mixed IDs, include_associations and include_coloc_pairs | done | |
| all_genes | `GpmapClient.all_genes` | `genes_api` | `/v1/genes` | none | extract `genes` | dataframe | non-empty and empty payload | done | |
| gene | `GpmapClient.gene` | `gene_api` | `/v1/genes/{id}` | gene_id required | cleanup + optional association merge | dict+dataframe | include flags behavior | done | |
| genes | `GpmapClient.genes` | `specific_genes_api` | `/v1/genes?...` | max 10 ids, no nulls | dedupe ids + optional association merge | dict+dataframe | limit and empty and flags | done | |
| variant | `GpmapClient.variant` | `variant_api`, `variant_summary_stats_api` | `/v1/variants/{id}`, `/v1/variants/{id}/summary-stats` | snp_id required | optional summary stats, merge associations | dict+dataframe | summary-stats extraction | done | |
| variants | `GpmapClient.variants` | `variants_api` | `/v1/variants?...` | max 10 expand, max 50 non-expand | dedupe + optional association merge | dict+dataframe | expand and non-expand limits | done | |
| region | `GpmapClient.region` | `region_api` | `/v1/regions/{id}` | region_id required | cleanup + optional association merge | dict+dataframe | include flags behavior | done | |
| ld_matrix | `GpmapClient.ld_matrix` | `ld_matrix_by_variant_api`, `ld_matrix_by_snp_id_api` | `/v1/ld/matrix?...` | variant_ids required | numeric vs string branch | dict/dataframe | snp_id and variant_id paths | done | |
| ld_proxies | `GpmapClient.ld_proxies` | `ld_proxies_by_variant_api`, `ld_proxies_by_snp_id_api` | `/v1/ld/proxies?...` | variant_ids required | numeric vs string branch | dict/dataframe | snp_id and variant_id paths | done | |
| associations | `GpmapClient.associations` | `associations_api` | `/v1/associations?...` | snp_ids and study_ids required | extract `associations` | dataframe | id filtering and empty response | done | |
| get_all_gene_pleiotropies | `GpmapClient.get_all_gene_pleiotropies` | `gene_pleiotropies_api` | `/v1/pleiotropy/genes` | none | extract `genes` | dataframe | non-empty and empty payload | done | |
| get_all_snp_pleiotropies | `GpmapClient.get_all_snp_pleiotropies` | `snp_pleiotropies_api` | `/v1/pleiotropy/snps` | none | extract `snps` | dataframe | non-empty and empty payload | done | |
| get_gwas | `GpmapClient.get_gwas` | `get_gwas_api` | `/v1/gwas/{id}`, `/v1/gwas/{id}/summary-stats` | gwas_id required | optional summary stats fetch | dict+dataframe | with and without summary stats | done | |
| upload_gwas | `GpmapClient.upload_gwas` | `upload_gwas_api` | `/v1/gwas` | file exists,<1GB; category/ancestry/reference_build; thresholds | multipart upload + JSON request | dict | validation failures + success | done | |
