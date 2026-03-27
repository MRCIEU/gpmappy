# Quickstart

```python
from gpmappy import GpmapClient

client = GpmapClient()
print(client.health_api())

results = client.search_gpmap("haemoglobin")  # DataFrame if pandas is installed
print(results.head())

portable_results = client.search_gpmap("haemoglobin", as_dataframe=False)  # list[dict]
print(portable_results[:2])
```

Module-level wrappers are also available:

```python
from gpmappy import health_api, search_gpmap

print(health_api())
print(search_gpmap("WNT7B"))
```

For nested objects like `gene()` outputs, table-like sections are also coerced to
DataFrames when pandas is available.
