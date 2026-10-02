# Reference models (kept out of the repo)

Put purchased reference models here. Git ignores everything in this folder except this README.
**Never commit them.** The Vela3D files are a paid Cults3D download, and their licence does not
allow redistribution. Only dimensions derived from them (`params/reference_vela3d.json`) are in
the repo, as the brief allows.

Expected file:

| File | What it is |
|---|---|
| `TOYOTA_RAV4_TRAY_DRAWER_ORGANIZER_MODULE.stl` | Vela3D "Toyota RAV4 Tray Drawer Organizer": the drawer housing. The comparison uses this one. |
| `..._LEFT.stl`, `..._RIGHT.stl` | the two drawers (mirror images). Not used. |

With the file in place:

```bash
python tools/rav4shelf.py reference          # compare + out/reference_compare.svg
python -m pytest tests/test_reference.py     # the same as unit tests
```

The comparison checks the file's bounding box (235.20 × 89.41 × 120.88 mm after un-rotating).
Another version of the model, or the other dash variant, gets skipped with a message. It would
need its own `ReferenceSpec` in `src/rav4shelf/reference.py`.
