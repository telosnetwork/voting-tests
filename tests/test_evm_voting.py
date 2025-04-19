from tests.setup import init_evm, create_eosio_linked_address, deploy_erc20, deploy_stlos, deploy_vote_manager, \
    update_system_contract
from tests.bp_voting import bp_voting
from tevmtest import CLEOSEVM

def test_evm():
    print("\nStarting EVM test...")
    cleos = CLEOSEVM.default()
    try:
        eosio_account = cleos.get_account("eosio")
    except Exception as e:
        print(f"Error getting eosio account: {e}")
        raise e

    native_account, linked_address, eth_address1, eth_address2 = init_evm(cleos)
    eosio_evm_address = create_eosio_linked_address(cleos)
    print(f"Native account: {native_account} with linked address: {linked_address}")
    print(f"ETH address 1: {eth_address1.address}")
    print(f"ETH address 2: {eth_address2.address}")

    erc20_contract = deploy_erc20(cleos, eth_address1)
    print(f"erc20 contract address: {erc20_contract.address}")

    stlos_contract = deploy_stlos(cleos, eth_address1, erc20_contract)
    print(f"stlos contract address: {stlos_contract.address}")

    manager_contract = deploy_vote_manager(cleos, eth_address1, eosio_evm_address, stlos_contract)
    print(f"manager contract address: {manager_contract.address}")

    update_system_contract(cleos)

    print("Setup complete, running tests...")

    bp_voting(cleos, native_account, eth_address1, eth_address2, erc20_contract, stlos_contract, manager_contract)
