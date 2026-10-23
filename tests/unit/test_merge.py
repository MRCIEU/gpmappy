from gpmappy.merge import merge_associations

BETA = 0.1


def test_merge_associations() -> None:
    coloc = [{"study_id": 1, "variant_id": 2}]
    rare = [{"study_id": 1, "variant_id": 2}]
    assoc = [{"study_id": 1, "variant_id": 2, "beta": BETA}]

    coloc_new, rare_new, _ = merge_associations(coloc, rare, assoc)
    assert isinstance(coloc_new, list)
    assert isinstance(rare_new, list)
    assert coloc_new[0]["beta"] == BETA
    assert rare_new[0]["beta"] == BETA
