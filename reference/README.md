# Reference model (kept out of the repo)

The starting values for the cubby's side walls and rear corners were estimated from a third-party
model, called the **cubby-constraint-reference-model** in this project. It was made for a slightly
different RAV4 version (its roof doesn't match the GR Sport PHEV), so it is only a starting point
that the test prints check. It may not be redistributed, so git ignores everything in this folder
except this README. **Never commit it.** Only the numbers fitted to it are in the repo:
`params/cubby_reference_fit.json`. `params/default.json` starts from them, except for the roof.

If you have the file, save it here as `cubby-constraint-reference-model.stl`, then:

```bash
python tools/rav4shelf.py reference          # compare + re-fit + out/reference_compare.svg
python tools/rav4shelf.py reference --write-params params/cubby_reference_fit.json   # update the record
python -m pytest tests/test_reference.py     # the same as unit tests
```

The tools check the file's bounding box (235.20 × 89.41 × 120.88 mm after undoing its placement).
A different file is skipped with a message; it would need its own `ReferenceSpec` in
`src/rav4shelf/reference.py`.
