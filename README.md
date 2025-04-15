# Telos EVM 2.0 python testing example

Requirements:

 - launch test container: https://github.com/guilledk/testcontainer-nodeos-evm/tree/oc_enabled
 - python uv: https://docs.astral.sh/uv/

Usage:

    uv venv .venv
    uv sync
    uv run pytest tests/test_example.py
