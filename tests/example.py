from eth_account import Account

from tevmtest import CLEOSEVM
from tevmtest.utils import to_wei

from leap.protocol import Asset
from leap.sugar import random_string


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 21000


def test_evm():
    cleos = CLEOSEVM.default()

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

    # test actuall tx send & fetch receipt
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

    def deploy_new_erc20(owner: str, name: str, symbol: str):
        return cleos.eth_deploy_contract_from_files(
            'tests/evm-contracts/ERC20/TestERC20.abi',
            'tests/evm-contracts/ERC20/TestERC20.bin',
            name,
            constructor_arguments=[owner, name, symbol]
        )

    # test erc20 contract deploy
    supply = to_wei(69, 'ether')
    name = 'TestToken'
    symbol = 'TT'
    erc20_contract, receipt = deploy_new_erc20(first_addr.address, name, symbol)

    cleos.wait_evm_block(receipt['blockNumber'] + 3)

    code = cleos.w3.eth.get_code(erc20_contract.address)
    assert code

    assert erc20_contract.functions.name().call() == name
    assert erc20_contract.functions.symbol().call() == symbol

    # Mint
    tx_args = {
        'from': first_addr.address,
        'gas': to_wei(0.1, 'telos'),
        'gasPrice': DEFAULT_GAS_PRICE,
        'nonce': 1,
        'chainId': cleos.evm_chain_id
    }
    erc20_tx = erc20_contract.functions.mint(
        first_addr.address,
        supply
    ).build_transaction(tx_args)
    signed_tx = Account.sign_transaction(erc20_tx, first_addr.key)
    tx_hash = cleos.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    assert erc20_contract.functions.totalSupply().call() == supply
