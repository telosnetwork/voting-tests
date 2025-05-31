from eth_account import Account
from leap.sugar import Asset, random_string
from tevmtest import CLEOSEVM


def test_generate_chain(cleos_full_bootstrap):
    cleos = cleos_full_bootstrap

    cleos.get_account('eosio')

    # Set max_tx_time to 199ms
    params = {
        "max_block_net_usage": 1048576,
        "target_block_net_usage_pct": 1000,
        "max_transaction_net_usage": 600000,
        "base_per_transaction_net_usage": 12,
        "net_usage_leeway": 500,
        "context_free_discount_net_usage_num": 20,
        "context_free_discount_net_usage_den": 100,
        "max_block_cpu_usage": 200000,
        "target_block_cpu_usage_pct": 500,
        "max_transaction_cpu_usage": 199000,
        "min_transaction_cpu_usage": 100,
        "max_transaction_lifetime": 3600,
        "deferred_trx_expiration_window": 600,
        "max_transaction_delay": 3888000,
        "max_inline_action_size": 524287,
        "max_inline_action_depth": 10,
        "max_authority_depth": 6,
        "max_action_return_value_size": 256
    }
    cleos.push_action(
        'eosio', 'setparams', [params], 'eosio')

    cleos = CLEOSEVM.from_cleos(cleos)

    cleos.deploy_evm()

    # Generate one new random native address
    account = cleos.new_account(name='evmuser')

    # Generate paired eth address
    cleos.create_evm_account(account, random_string())
    native_eth_addr = cleos.eth_account_from_name(account)

    # Generate two regular eth address
    first_addr = Account.create()

    # Give tokens from system to test account
    cleos.transfer_token('eosio', account, Asset.from_str('101000000.0000 TLOS'), 'evm test')

    # Deposit tokens into evm test account
    cleos.transfer_token(account, 'eosio.evm', Asset.from_str('101000000.0000 TLOS'), 'Deposit')

    # Withdraw tokens from evm test account
    cleos.eth_withdraw('1.0000 TLOS', account)

    # Perform nativly signed transfer
    cleos.eth_transfer_via_native(
        native_eth_addr,
        first_addr.address,
        Asset.from_str('10000000.0000 TLOS'),
        account=account
    )

    cleos.wait_blocks(1)

    cleos.push_action(
        'eosio.evm', 'setrevision', [1], 'eosio.evm')

    cleos.wait_blocks(1)
