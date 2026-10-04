import json
import os
import sys

import pytest

from rav4shelf import params

from conftest import REPO

sys.path.insert(0, os.path.join(REPO, "tools"))
import gen_param_docs  # noqa: E402


def test_parameter_reference_is_up_to_date():
    with open(os.path.join(REPO, "docs", "parameters.md"), encoding="utf-8") as f:
        assert f.read() == gen_param_docs.render(), \
            "docs/parameters.md is stale: run python tools/gen_param_docs.py"


def test_measured_example_lists_every_guess_and_nothing_unknown():
    spec = params.load_spec()
    with open(os.path.join(REPO, "params", "measured.example.json"), encoding="utf-8") as f:
        example = json.load(f)
    keys = {k for k in example if not k.startswith("_")}
    assert keys <= set(spec)
    guesses = {n for n, s in spec.items() if s.get("placeholder") and s.get("basis") != "reference"}
    assert guesses <= keys
    assert all(example[n] is None for n in guesses)


def test_unfilled_example_gives_a_helpful_error():
    with pytest.raises(params.ParamError) as exc:
        params.load_params(os.path.join(REPO, "params", "measured.example.json"))
    assert "fill in a value" in str(exc.value)


def test_docs_mention_every_placeholder():
    with open(os.path.join(REPO, "docs", "measuring.md"), encoding="utf-8") as f:
        text = f.read()
    missing = [n for n in params.load_params().placeholders if "`%s`" % n not in text]
    assert not missing, "docs/measuring.md does not explain: %s" % missing


def _slug(heading):
    """GitHub's anchor for a Markdown heading."""
    import re
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def test_relative_links_in_markdown_resolve():
    import glob
    import re
    files = glob.glob(os.path.join(REPO, "*.md")) + glob.glob(os.path.join(REPO, "*", "*.md"))
    broken = []
    for md in files:
        text = open(md, encoding="utf-8").read()
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if "://" in target or target.startswith("mailto:"):
                continue
            path, _, anchor = target.partition("#")
            dest = os.path.normpath(os.path.join(os.path.dirname(md), path)) if path else md
            if not os.path.exists(dest):
                broken.append("%s: %s" % (os.path.relpath(md, REPO), target))
            elif anchor and dest.endswith(".md"):
                headings = re.findall(r"^#+ (.+)$", open(dest, encoding="utf-8").read(), re.M)
                if anchor not in {_slug(h) for h in headings}:
                    broken.append("%s: %s (no such heading)" % (os.path.relpath(md, REPO), target))
    assert not broken, broken
