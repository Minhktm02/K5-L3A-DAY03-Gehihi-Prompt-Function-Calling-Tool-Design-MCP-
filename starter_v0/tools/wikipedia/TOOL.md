---
name: wikipedia
track: bonus
kind: live_api
provider: Wikipedia
requires_env: []
inputs: [query, lang, max_results]
outputs: [items]
side_effect: false
---
# wikipedia

Searches Wikipedia for encyclopedic knowledge, definitions of concepts, biographies, and factual backgrounds.
Returns a list of items with title, summary extract, and reference URL.

