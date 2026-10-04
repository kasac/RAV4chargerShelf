# Reference model (kept out of the repo)

The cubby envelope's defaults were estimated from a reference model of the cubby, called the
**cubby-constraint-reference-model** in this project. It stands in for a 3D scan of the car's
cavity, and it is used only to estimate the cavity's size and shape. It is a third-party file
that may not be redistributed, so git ignores everything in this folder except this README.
**Never commit it.** Only the ~15 numbers describing the cavity are in the repo:
`params/cubby_reference_fit.json`, which are also the defaults in `params/default.json`.

If you have the file, save it here as `cubby-constraint-reference-model.stl`, then:

```bash
python tools/rav4shelf.py reference          # compare + re-fit + out/reference_compare.svg
python tools/rav4shelf.py reference --write-params params/cubby_reference_fit.json   # update the record
python -m pytest tests/test_reference.py     # the same as unit tests
```

The tools check the file's bounding box (235.20 × 89.41 × 120.88 mm after undoing its placement).
A different file is skipped with a message; it would need its own `ReferenceSpec` in
`src/rav4shelf/reference.py`.
