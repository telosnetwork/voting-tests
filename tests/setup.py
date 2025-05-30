from hashlib import sha256
import json
from pathlib import Path
from time import sleep

from eth_account import Account
from leap.protocol import Asset, ABI
from leap.errors import ChainAPIError
from leap.sugar import random_string

from tevmtest import to_wei, remove_0x_prefix

DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21000

def init_evm(cleos):
    # Test connection
    assert cleos.w3.is_connected()

    # Test gas price
    gas_price = cleos.w3.eth.gas_price
    assert gas_price <= 120000000000

    # Test chain ID
    assert cleos.w3.eth.chain_id == cleos.evm_chain_id
    evm_contract_dir = './tests/contracts/eosio.evm/regular'

    with open(evm_contract_dir + '/regular.wasm', 'rb') as wasm_file:
        evm_wasm = wasm_file.read()

    local_hash = sha256(evm_wasm).hexdigest()
    remote_hash, remote_bytes = cleos.get_code('eosio.evm')
    if local_hash == remote_hash:
        cleos.logger.info("System contract is up to date")
    else:
        # Redeploy EVM contract to ensure debug is not enabled as that will crash translator if there is a revert
        deploy_result = cleos.deploy_contract_from_path(
            'eosio.evm',
            evm_contract_dir,
            privileged=False,
            create_account=False
        )

    # Need to create this for delegatebw to work
    try:
        cleos.get_account('telos.decide')
    except ChainAPIError:
        cleos.new_account('telos.decide', key=cleos.keys['eosio'])

    account = cleos.new_account()
    sleep(3)
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
    cleos.eth_transfer_via_native(native_eth_addr, first_addr.address, Asset.from_str('9000000.0000 TLOS'), account=account)

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
    tx_hash = cleos.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = cleos.w3.eth.wait_for_transaction_receipt(tx_hash)
    assert receipt

    # verify block hash in receipt is valid (metamask does this after getting a receipt)
    block = cleos.w3.eth.get_block(receipt['blockHash'])
    assert block['hash'] == receipt['blockHash']

    cleos.push_action(
        'eosio.evm', 'setrevision', [1], 'eosio.evm')

    cleos.wait_evm_blocks(1)

    return account, eth_addr, first_addr, second_addr


def create_eosio_linked_address(cleos):
    native_eth_addr = cleos.eth_account_from_name('eosio')
    if native_eth_addr is None:
        cleos.create_evm_account('eosio', random_string())
        native_eth_addr = cleos.eth_account_from_name('eosio')

    return cleos.w3.to_checksum_address(native_eth_addr)


def deploy_erc20(cleos, owner_addr):
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

    tx_hash = cleos.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    assert erc20_contract.functions.totalSupply().call() == supply
    return erc20_contract


def deploy_stlos(cleos, owner_addr, erc20_contract):
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


def deploy_vote_manager(cleos, deployer_addr, stlos_contract):
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

    return manager_contract

def set_evm_owner(cleos, manager_contract, deployer_addr, eosio_addr):
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

    transfer_ownership_tx_hash = cleos.w3.eth.send_raw_transaction(transfer_ownership_signed_trx.raw_transaction)
    transfer_ownership_receipt = cleos.w3.eth.wait_for_transaction_receipt(transfer_ownership_tx_hash)

    cleos.wait_evm_block(transfer_ownership_receipt['blockNumber'] + 3)

    # Verify the owner is set correctly
    assert manager_contract.functions.owner().call() == eosio_addr

def update_system_contract(cleos):
    abi_result = cleos.get_abi('eosio')
    assert abi_result

    system_contract_path = Path('../telos.contracts/build/contracts/eosio.system')

    with open(system_contract_path / 'eosio.system.wasm', 'rb') as wasm_file:
        system_wasm = wasm_file.read()

    local_hash = sha256(system_wasm).hexdigest()
    remote_hash, remote_bytes = cleos.get_code('eosio')
    if local_hash == remote_hash:
        cleos.load_abi_file('eosio', system_contract_path / 'eosio.system.abi')
        cleos.logger.info("System contract is up to date")
        return

    cleos.get_account('eosio')

    cleos.deploy_contract_from_path(
        'eosio',
        system_contract_path,
        contract_name='eosio.system',
        create_account=False,
    )

    cleos.get_account('eosio')
    # abi_result = cleos.get_abi('eosio')
    # assert abi_result
    # cleos.load_abi('eosio', abi_result)

def set_vote_manager(cleos, manager_contract):
    # Set the vote manager contract in the system contract
    mgr_address = remove_0x_prefix(manager_contract.address)
    # mgr_address = ('0' * (12 * 2)) + mgr_address
    # mgr_address = bytes.fromhex(mgr_address)
    cleos.push_action(
        'eosio',
        'setvotecontr',
        [mgr_address],
        'eosio',
        key=cleos.private_keys['eosio']
    )
    cleos.logger.info(f"Set vote manager to {manager_contract.address}")
    row = cleos.get_table('eosio', 'eosio', 'votingconfig')[0]
    assert f'0x{row["evm_voting_contract"]}'== manager_contract.address.lower()
