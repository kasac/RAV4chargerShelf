import os
import sys

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, os.path.join(REPO, "src"))

from rav4shelf import params  # noqa: E402


@pytest.fixture
def p():
    """Defaults only, never the user's params/measured.json."""
    return params.load_params()


@pytest.fixture
def d(p):
    return params.derive(p)


def make(**overrides):
    """(Params, Derived) from defaults plus overrides."""
    pp = params.load_params(overrides)
    return pp, params.derive(pp)
