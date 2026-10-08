# Reference models (kept out of the repo)

Optional: compare the cubby model with another model's STL. Third-party files may not be
redistributable, so git ignores this folder except this README. **Never commit them.**

Save the file as `cubby-constraint-reference-model.stl`, then:

```bash
python tools/rav4shelf.py reference          # compare and re-fit; out/reference_compare.svg
python tools/rav4shelf.py reference --write-params params/cubby_reference_fit.json
python -m pytest tests/test_reference.py
```

The tools expect the model they were set up for (bounding box 235.20 × 89.41 × 120.88 mm); another
file needs its own `ReferenceSpec` in `src/rav4shelf/reference.py`.
