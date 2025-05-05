from antelope_rs.antelope_rs import Asset
from eth_account import Account

from tests.voting_utils import stake_erc20
from tevmtest import to_wei, DEFAULT_GAS_PRICE


def check_decay(cleos, native_funder, evm_funder, erc20_contract, stlos_contract, manager_contract):
    # Create 2 new accounts on each of EVM/native
    ( alice_evm, alice_namtive ) = create_voters(cleos, native_funder, evm_funder, erc20_contract, stlos_contract, manager_contract)
    ( bob_evm, bob_native ) = create_voters(cleos, native_funder, evm_funder, erc20_contract, stlos_contract, manager_contract)

    # Vote for 30 producers in EVM with first account
    # Vote for 30 producers in native with first account
    # Check that the votes are the same in both contracts
    # Set decay values to decay 15% per year, starting 1 yr + 1 day ago
    # Vote for 30 producers in EVM with second account, same amount
    # Vote for 30 producers in native with second account, same amount
    # Check that the votes are the same in both contracts
    # Check that the votes of second account are greater than the first account from before decay values were set


# Return tuple of native_account, evm_address, also transferring some TLOS to each
def create_voters(cleos, native_funder, evm_funder, erc20_contract, stlos_contract, manager_contract, amount=1_000_000):
    evm_address = Account.create()
    native_account = cleos.new_account()

    # Transfer some TLOS to the new accounts
    quantity = Asset.from_str(f"{amount}.0000 TLOS")
    cleos.transfer_token(native_funder, native_account, quantity, 'evm test')

    # Stake TLOS on native side to vote with
    half_amount = str(amount / 2).split('.')[0]
    resource_amount = Asset.from_str(f"{half_amount}.0000 TLOS")
    cleos.delegate_bandwidth(native_account, native_account, resource_amount, resource_amount, False)

    # Transfer TLOS for some gas
    cleos.eth_transfer(
        evm_funder,
        evm_address.address,
        to_wei(100, 'ether'),
    )

    amount_wei = to_wei(amount, 'ether')
    cleos.eth_build_and_send_transaction(
        erc20_contract.functions.transfer(evm_address.address, amount_wei),
        evm_address,
        100000,
        DEFAULT_GAS_PRICE
    )

    # Stake to STLOS > deposit STLOS to vote manager
    stake_erc20(
        cleos,
        evm_address,
        erc20_contract,
        stlos_contract,
        manager_contract,
        amount_wei
    )


    return (evm_address, native_account)