# Deprecated Files

These files are no longer actively used and are kept for reference only.

## Files

- `pipeline_old.py` - Original pipeline using legacy extractor/matcher
- `improved_pipeline.py` - Duplicate of current pipeline.py
- `product_extractor.py` - Legacy extractor, replaced by `improved_product_extractor.py`
- `product_matcher.py` - Legacy matcher, replaced by `improved_product_matcher.py`

## Migration

All active code now uses:
- `pipeline.py` (main pipeline)
- `improved_product_extractor.py`
- `improved_product_matcher.py`
