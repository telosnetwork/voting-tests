# Telos EVM 2.0 python testing example

Requirements:

 - `evm-voting` and `telos.contracts` repos are siblings of this repo (same parent directory) and they have compiled their respective contracts
 - launch test container: https://github.com/telosnetwork/testcontainer-nodeos-evm/tree/evm_voting_changes
 - python uv: https://docs.astral.sh/uv/

Usage:

    uv venv .venv
    uv sync
    uv run pytest tests/test_evm_voting.py
