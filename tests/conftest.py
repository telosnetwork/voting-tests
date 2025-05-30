import pytest

from leap.fixtures import bootstrap_test_nodeos

from tevmtest import CLEOSEVM


@pytest.fixture
def cleos_full_bootstrap(request, tmp_path_factory):
    request.applymarker(pytest.mark.bootstrap(True))
    request.applymarker(pytest.mark.randomize(False))
    request.applymarker(pytest.mark.extra_plugins('state_history_plugin'))
    with bootstrap_test_nodeos(request, tmp_path_factory) as cleos:
        yield cleos


@pytest.fixture(scope='session')
def cleosevm() -> CLEOSEVM:
    cleos =  CLEOSEVM.default()
    cleos.w3.eth.handleRevert = True

    return cleos
