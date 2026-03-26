# Quickstart

```python
from gpmappy import GpmapClient

client = GpmapClient()
print(client.health_api())

results = client.search_gpmap("haemoglobin")
print(results.head())
```

Module-level wrappers are also available:

```python
from gpmappy import health_api, search_gpmap

print(health_api())
print(search_gpmap("WNT7B"))
```
