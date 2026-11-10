---
name: github_search
track: bonus
kind: live_api
provider: GitHub REST API
requires_env: []
inputs: [query, max_results]
outputs: [total_count, items]
side_effect: false
---
# github_search

Searches public GitHub issues and pull requests. It does not create or modify content.