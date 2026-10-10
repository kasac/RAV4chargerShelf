# Grasshopper setup, repo-linked (for code changes)

For the model alone, use the single Script component in
[grasshopper_onboarding.md](grasshopper_onboarding.md). This setup is for editing `src/`: one thin
wrapper component per part imports the code from your clone, and **reload** picks up your edits.

```
[sliders] ──► S ┐
[Panel] ─► groups│ PARAMS  P ──┬──► FIT COUPON     coupon ──► EXPORT (name = "fit_coupon")
[Button] ► sliders│            ├──► PROFILE GAUGE  gauge_print ──► EXPORT (name = "profile_gauge")
[Button] ► reload ┘            ├──► ROOF PLATE     roof
                               └──► CONTEXT        cubby, ports, phone
```

1. Clone the repo. In Rhino 8 (units: millimetres) open Grasshopper and save the empty definition as
   `<repo>/grasshopper/RAV4chargerShelf.gh`: the wrappers find `src/` from there. Elsewhere, set the
   environment variable `RAV4SHELF_REPO` to the repo folder.
2. For each file in [`rhino/gh_components/`](../rhino/gh_components/): place a **Python 3 Script**
   component, give it the inputs and outputs listed at the top of the file (zoom in for **⊕ / ⊖**,
   right-click to rename), and paste the file as its code.
3. Wire them as above. On the Params component, input **`S`** must be **List Access**.

**Params:** values apply in this order, later wins: `default.json` < `params/measured.json` <
`overrides` file < sliders. The **sliders** button creates wired sliders for the groups in the
`groups` Panel (e.g. `cubby,fit,coupon`; empty = all). **reload** re-imports the modules after you
edit a `.py` file or pull; Rhino otherwise caches them until it restarts.

**Export:** writes STL, 3MF (the repo's own writer) and STEP (Rhino's exporter) in print orientation
to `out/`; if STEP fails from Grasshopper, run `rhino/build_all.py` in the ScriptEditor.

The wrappers only change when a component's inputs or outputs change; then paste them again. Report
problems with the exact message: [README → First run in Rhino](../README.md#first-run-in-rhino).
