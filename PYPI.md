# gpmappy

Python client for the OpenGWAS genotype-phenotype map API.

## Install

Base install:

```bash
pip install gpmappy
```

Install with DataFrame support:

```bash
pip install "gpmappy[dataframe]"
```

## Quick start

```python
from gpmappy import GpmapClient

client = GpmapClient()

health = client.health_api()
print(health)

results = client.search_gpmap("haemoglobin")
print(results.head() if hasattr(results, "head") else results[:5])
```

## Output behavior

- Table-like outputs return pandas DataFrames when pandas is installed.
- Without pandas, table-like outputs return `list[dict]`.
- Use `as_dataframe=True` to require DataFrame output, or `as_dataframe=False` to force list output.

## Resources

- Documentation: https://MRCIEU.github.io/gpmappy/
- Source: https://github.com/MRCIEU/gpmappy
- Issues: https://github.com/MRCIEU/gpmappy/issues
