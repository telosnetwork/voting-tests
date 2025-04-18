import json

from eth_account import Account

from tevmtest import CLEOSEVM
from tevmtest.utils import to_wei

from leap.protocol import Asset
from leap.sugar import random_string


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21000

cleos = CLEOSEVM.default()

def test_evm():
    print("\nStarting EVM test...")
    native_account, linked_address, eth_address1, eth_address2 = init_evm()
    eosio_evm_address = create_eosio_linked_address()
    print(f"Native account: {native_account} with linked address: {linked_address}")
    print(f"ETH address 1: {eth_address1.address}")
    print(f"ETH address 2: {eth_address2.address}")

    erc20_contract = deploy_erc20(eth_address1)
    print(f"erc20 contract address: {erc20_contract.address}")

    stlos_contract = deploy_stlos(eth_address1, erc20_contract)
    print(f"stlos contract address: {stlos_contract.address}")

    manager_contract = deploy_vote_manager(eth_address1, eosio_evm_address, stlos_contract)
    print(f"manager contract address: {manager_contract.address}")

    update_system_contract()


def init_evm():
    # Test connection
    assert cleos.w3.is_connected()

    # Test gas price
    gas_price = cleos.w3.eth.gas_price
    assert gas_price <= 120000000000

    # Test chain ID
    assert cleos.w3.eth.chain_id == cleos.evm_chain_id

    # Test transaction count
    account = cleos.new_account()
    cleos.create_evm_account(account, random_string())
    eth_addr = cleos.eth_account_from_name(account)
    assert eth_addr
    quantity = Asset.from_str('10000.0000 TLOS')
    cleos.transfer_token('eosio', account, quantity, 'evm test')
    cleos.transfer_token(account, 'eosio.evm', quantity, 'Deposit')
    assert cleos.eth_get_transaction_count(eth_addr) == 1

    # Test get transaction receipt
    account = cleos.new_account()
    cleos.create_evm_account(account, random_string())
    native_eth_addr = cleos.eth_account_from_name(account)
    first_addr = Account.create()
    second_addr = Account.create()
    cleos.transfer_token('eosio', account, Asset.from_str('20000000.0000 TLOS'), 'evm test')
    cleos.transfer_token(account, 'eosio.evm', Asset.from_str('10000000.0000 TLOS'), 'Deposit')
    cleos.eth_transfer(native_eth_addr, first_addr.address, Asset.from_str('9000000.0000 TLOS'), account=account)

    cleos.wait_evm_blocks(1)

    quantity = 420
    tx_params = {
        'from': first_addr.address,
        'to': second_addr.address,
        'gas': DEFAULT_GAS,
        'gasPrice': DEFAULT_GAS_PRICE,
        'value': quantity,
        'data': b'',
        'nonce': 0,
        'chainId': cleos.evm_chain_id
    }

    # test actually tx send & fetch receipt
    signed_tx = Account.sign_transaction(tx_params, first_addr.key)
    tx_hash = cleos.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = cleos.w3.eth.wait_for_transaction_receipt(tx_hash)
    assert receipt

    # verify block hash in receipt is valid (metamask does this after getting a receipt)
    block = cleos.w3.eth.get_block(receipt['blockHash'])
    assert block['hash'] == receipt['blockHash']

    cleos.push_action(
        'eosio.evm', 'setrevision', [1], 'eosio.evm')

    cleos.wait_evm_blocks(1)

    return account, eth_addr, first_addr, second_addr

def create_eosio_linked_address():
    cleos.create_evm_account('eosio', random_string())
    native_eth_addr = cleos.eth_account_from_name('eosio')
    return native_eth_addr

def deploy_erc20(owner_addr):
    # test erc20 contract deploy
    supply = to_wei(10000000, 'ether')
    name = 'MockWTLOS'
    symbol = 'WTLOS'
    erc20_contract, receipt = cleos.eth_deploy_contract_from_files(
        'tests/evm-contracts/ERC20/TestERC20.abi',
        'tests/evm-contracts/ERC20/TestERC20.bin',
        name,
        constructor_arguments=[owner_addr.address, name, symbol]
    )

    cleos.wait_evm_block(receipt['blockNumber'] + 3)

    code = cleos.w3.eth.get_code(erc20_contract.address)
    assert code

    assert erc20_contract.functions.name().call() == name
    assert erc20_contract.functions.symbol().call() == symbol

    # Mint
    tx_args = {
        'from': owner_addr.address,
        'gas': to_wei(0.1, 'telos'),
        'gasPrice': DEFAULT_GAS_PRICE,
        'nonce': 1,
        'chainId': cleos.evm_chain_id
    }
    erc20_tx = erc20_contract.functions.mint(
        owner_addr.address,
        supply
    ).build_transaction(tx_args)
    signed_tx = Account.sign_transaction(erc20_tx, owner_addr.key)

    tx_hash = cleos.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    assert erc20_contract.functions.totalSupply().call() == supply
    return erc20_contract

def deploy_stlos(owner_addr, erc20_contract):
    name = 'Mock STLOS'
    symbol = 'mSTLOS'
    stlos_json_path = '../evm-voting/out/MockSTLOSVault.sol/MockSTLOSVault.json'
    with open(stlos_json_path, 'r') as stlos_fp:
        stlos_json = json.load(stlos_fp)

    # instantiate
    Contract = cleos.w3.eth.contract(
        abi=stlos_json['abi'],
        bytecode=stlos_json['bytecode']['object'],
    )
    constructor_arguments = [erc20_contract.address]

    stlos_contract, receipt = cleos.eth_deploy_contract(
        Contract, stlos_json['abi'], name,
        constructor_arguments=constructor_arguments,
        account=owner_addr
    )

    cleos.wait_evm_block(receipt['blockNumber'] + 3)

    code = cleos.w3.eth.get_code(stlos_contract.address)
    assert code

    assert stlos_contract.functions.name().call() == name
    assert stlos_contract.functions.symbol().call() == symbol

    return stlos_contract

def deploy_vote_manager(deployer_addr, eosio_addr, stlos_contract):
    name = 'BPVoteManager'
    manager_json_path = '../evm-voting/out/BPVoteManager.sol/BPVoteManager.json'
    with open(manager_json_path, 'r') as manager_fp:
        manager_json = json.load(manager_fp)

    # instantiate
    Contract = cleos.w3.eth.contract(
        abi=manager_json['abi'],
        bytecode=manager_json['bytecode']['object'],
    )
    constructor_arguments = [stlos_contract.address]

    manager_contract, receipt = cleos.eth_deploy_contract(
        Contract, manager_json['abi'], name,
        constructor_arguments=constructor_arguments,
        account=deployer_addr
    )

    cleos.wait_evm_block(receipt['blockNumber'] + 3)

    code = cleos.w3.eth.get_code(manager_contract.address)
    assert code

    assert manager_contract.functions.stlosVault().call() == stlos_contract.address

    # Set eosio EVM address as owner
    transfer_ownership_nonce = cleos.w3.eth.get_transaction_count(deployer_addr.address)

    tx_args = {
        'from': deployer_addr.address,
        'gas': to_wei(0.1, 'telos'),
        'gasPrice': DEFAULT_GAS_PRICE,
        'nonce': transfer_ownership_nonce,
        'chainId': cleos.evm_chain_id
    }

    transfer_ownership_trx = manager_contract.functions.transferOwnership(
        eosio_addr,
    ).build_transaction(tx_args)

    transfer_ownership_signed_trx = Account.sign_transaction(transfer_ownership_trx, deployer_addr.key)

    transfer_ownership_tx_hash = cleos.w3.eth.send_raw_transaction(transfer_ownership_signed_trx.rawTransaction)
    transfer_ownership_receipt = cleos.w3.eth.wait_for_transaction_receipt(transfer_ownership_tx_hash)

    cleos.wait_evm_block(transfer_ownership_receipt['blockNumber'] + 3)

    # Verify the owner is set correctly
    assert manager_contract.functions.owner().call() == eosio_addr
    return manager_contract


def update_system_contract():
    system_wasm_path = '../telos.contracts/build/contracts/eosio.system/eosio.system.wasm'
    system_abi_path = '../telos.contracts/build/contracts/eosio.system/eosio.system.abi'

    system_wasm = open(system_wasm_path, 'rb').read()
    system_abi = open(system_abi_path, 'r').read()
    system_abi_json = json.loads(system_abi)

    with open(system_abi_path, 'r') as abi_fp:
        system_abi = json.load(abi_fp)

    deploy_result = cleos.deploy_contract(
        "eosio",
        system_wasm,
        system_abi_json,
    )