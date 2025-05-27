from antelope_rs.antelope_rs import Asset
from eth_account import Account

from tests.voting_utils import deposit_and_stake_erc20, vote_evm, vote_native, producers, stake_erc20, \
    assert_bp_voteweight
from tevmtest import to_wei, DEFAULT_GAS_PRICE
from tevmtest.utils import s2n


def check_decay(cleos, native_funder, evm_funder, erc20_contract, stlos_contract, manager_contract):
    amount = 1_000_000
    producer_names = producers[:30]
    assert_bp_voteweight(cleos, manager_contract, producer_names, 0)
    # Create 2 new accounts on each of EVM/native, this also deposits and stakes
    ( alice_evm, alice_native ) = create_voters(cleos, native_funder, evm_funder, erc20_contract, stlos_contract, manager_contract, amount)
    ( bob_evm, bob_native ) = create_voters(cleos, native_funder, evm_funder, erc20_contract, stlos_contract, manager_contract, amount)

    # Vote for 30 producers in EVM and native with first account
    vote(cleos, alice_evm, alice_native, manager_contract, producer_names)
    assert_bp_voteweight(cleos, manager_contract, producer_names, amount)

    # Check that the votes are the same in both contracts
    # Set decay values to decay 15% per year, starting 1 yr + 1 day ago
    # Vote for 30 producers in EVM with second account, same amount
    # Vote for 30 producers in native with second account, same amount
    # Check that the votes are the same in both contracts
    # Check that the votes of second account are greater than the first account from before decay values were set
    # Reset votes to 0

# Return tuple of native_account, evm_address, also transferring some TLOS to each
def create_voters(cleos, native_funder, evm_funder, erc20_contract, stlos_contract, manager_contract, amount=1_000_000):
    evm_address = Account.create()
    # This creates an account with 10 TLOS to each of CPU/NET, it gets an extra 20 TLOS stake so we subtract 20 TLOS
    native_account = cleos.new_account()
    native_amount = amount - 20

    # Transfer some TLOS to the new accounts
    quantity = Asset.from_str(f"{native_amount}.0000 TLOS")
    cleos.transfer_token(native_funder, native_account, quantity, 'evm test')

    # Stake TLOS on native side to vote with
    half_amount = str(native_amount / 2).split('.')[0]
    resource_amount = Asset.from_str(f"{half_amount}.0000 TLOS")
    cleos.delegate_bandwidth(native_account, native_account, resource_amount, resource_amount, False)

    # Transfer TLOS for some gas
    cleos.eth_transfer(
        evm_funder,
        evm_address.address,
        to_wei(100, 'ether'),
    )

    # Create EVM account
    amount_wei = to_wei(amount, 'ether')
    cleos.eth_build_and_send_transaction(
        erc20_contract.functions.transfer(evm_address.address, amount_wei),
        evm_funder,
        100000,
        DEFAULT_GAS_PRICE
    )

    # Stake to STLOS > deposit STLOS to vote manager
    deposit_and_stake_erc20(
        cleos,
        evm_address,
        erc20_contract,
        stlos_contract,
        manager_contract,
        amount_wei
    )


    return (evm_address, native_account)

def vote(cleos, address, native_account, manager_contract, producer_names):
    cleos.logger.info("\nVoting for EVM decay test...")

    vote_evm(cleos, address, manager_contract, producer_names)
    cleos.logger.info(f"Voted with {address} for producers: {producer_names}")

    vote_native(cleos, native_account, producer_names)
    cleos.logger.info(f"Voted with {native_account} for producers: {producer_names}")
