from gpmappy.merge import merge_associations


def test_merge_associations() -> None:
    coloc = [{"study_id": 1, "snp_id": 2}]
    rare = [{"study_id": 1, "snp_id": 2}]
    assoc = [{"study_id": 1, "snp_id": 2, "beta": 0.1}]

    coloc_new, rare_new = merge_associations(coloc, rare, assoc)
    assert isinstance(coloc_new, list)
    assert isinstance(rare_new, list)
    assert coloc_new[0]["beta"] == 0.1
    assert rare_new[0]["beta"] == 0.1
