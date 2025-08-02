Add dogpile prevention (cache stampede mitigation) to prevent multiple simultaneous cache refreshes

When enabled, if multiple requests arrive for an expired cache entry:
- The first request will compute the new value
- Subsequent requests will wait briefly for the computation to complete
- All waiting requests will use the newly cached value once available

This feature can be configured globally or per-endpoint with customizable wait times and grace periods.