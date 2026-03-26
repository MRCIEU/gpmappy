import pandas as pd

from gpmappy.merge import merge_associations


def test_merge_associations() -> None:
    coloc = pd.DataFrame([{"study_id": 1, "snp_id": 2}])
    rare = pd.DataFrame([{"study_id": 1, "snp_id": 2}])
    assoc = pd.DataFrame([{"study_id": 1, "snp_id": 2, "beta": 0.1}])

    coloc_new, rare_new = merge_associations(coloc, rare, assoc)
    assert coloc_new is not None
    assert rare_new is not None
    assert "beta" in coloc_new.columns
    assert "beta" in rare_new.columns
