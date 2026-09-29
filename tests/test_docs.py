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


def test_measured_example_lists_every_placeholder_and_nothing_unknown():
    spec = params.load_spec()
    with open(os.path.join(REPO, "params", "measured.example.json"), encoding="utf-8") as f:
        example = json.load(f)
    keys = {k for k in example if not k.startswith("_")}
    assert keys <= set(spec)
    assert keys == {n for n, s in spec.items() if s.get("placeholder")}


def test_unfilled_example_gives_a_helpful_error():
    with pytest.raises(params.ParamError) as exc:
        params.load_params(os.path.join(REPO, "params", "measured.example.json"))
    assert "fill in a value" in str(exc.value)


def test_docs_mention_every_placeholder():
    with open(os.path.join(REPO, "docs", "measuring.md"), encoding="utf-8") as f:
        text = f.read()
    missing = [n for n in params.load_params().placeholders if "`%s`" % n not in text]
    assert not missing, "docs/measuring.md does not explain: %s" % missing
