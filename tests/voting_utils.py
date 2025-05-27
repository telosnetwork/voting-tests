from tevmtest import DEFAULT_GAS_PRICE
from tevmtest.utils import s2n


def deposit_and_stake_erc20(cleos, eth_address, erc20_contract, stlos_contract, manager_contract, amount):
    starting_stlos_balance = stlos_contract.functions.balanceOf(eth_address.address).call()
    cleos.logger.info(f"Starting STLOS balance for {eth_address.address}: {starting_stlos_balance}")

    approve_receipt = cleos.eth_build_and_send_transaction(
        erc20_contract.functions.approve(stlos_contract.address, amount),
        eth_address,
        100000,
        DEFAULT_GAS_PRICE
    )

    cleos.logger.info(f"Approved {amount} STLOS balance for {eth_address.address}")

    deposit_receipt = cleos.eth_build_and_send_transaction(
        stlos_contract.functions.deposit(amount, eth_address.address),
        eth_address,
        200000,
        DEFAULT_GAS_PRICE
    )

    ending_stlos_balance = stlos_contract.functions.balanceOf(eth_address.address).call()
    cleos.logger.info(f"Minted {amount} STLOS for {eth_address.address}, ending balance is {ending_stlos_balance}")
    stake_erc20(cleos, eth_address, erc20_contract, stlos_contract, manager_contract, amount)

def stake_erc20(cleos, eth_address, erc20_contract, stlos_contract, manager_contract, amount):
    approve_stlos_receipt = cleos.eth_build_and_send_transaction(
        stlos_contract.functions.approve(manager_contract.address, amount),
        eth_address,
        100000,
        DEFAULT_GAS_PRICE
    )

    stake_receipt = cleos.eth_build_and_send_transaction(
        manager_contract.functions.stake(amount),
        eth_address,
        200000,
        DEFAULT_GAS_PRICE
    )

    staked_balance = manager_contract.functions.userStakedBalance(eth_address.address).call()
    cleos.logger.info(f"Staked {amount} STLOS for {eth_address.address}, staked balance is {staked_balance}")

def unstake_erc20(cleos, eth_address, erc20_contract, stlos_contract, manager_contract, amount):
    unstake_receipt = cleos.eth_build_and_send_transaction(
        manager_contract.functions.unstake(amount),
        eth_address,
        200000,
        DEFAULT_GAS_PRICE
    )

    cleos.logger.info(f"Unstaked {amount} STLOS for {eth_address.address}")

def vote_evm(cleos, address, manager_contract, producer_names):
    cleos.logger.info(f"Making vote for {address}...")
    if producer_names and type(producer_names[0]) is str:
        producer_names = [s2n(x) for x in producer_names]

    vote_receipt = cleos.eth_build_and_send_transaction(
        manager_contract.functions.vote(sorted(producer_names)),
        address,
        4000000,
        DEFAULT_GAS_PRICE
    )
    cleos.logger.info(f"Vote receipt: {vote_receipt}")

def vote_native(cleos, account, producer_names):
    cleos.logger.info(f"Making vote for {account}...")
    cleos.vote_producers(account, '', sorted(producer_names));
    cleos.logger.info(f"Vote complete for {account}")

def assert_bp_voteweight(cleos, manager_contract, producer_names, vote_weight):
    vote_weight_wei = vote_weight * 10**18
    for producer in producer_names:
        evm_vote_weight = manager_contract.functions.totalVotes(s2n(producer)).call()
        native_producer = cleos.get_producer(producer)
        native_vote_weight = int(0)
        if native_producer:
            native_vote_weight = int(float(native_producer['total_votes'])) * 10**14

        assert evm_vote_weight == vote_weight_wei, f"Vote weight for {producer} is not {vote_weight_wei} after voting"
        assert native_vote_weight == vote_weight_wei, f"Vote weight for {producer} is not {vote_weight_wei} after voting"

producers = [
    "bp1",  "bp2",  "bp3",  "bp4",  "bp5",
    "bp11", "bp12", "bp13", "bp14", "bp15",
    "bp21", "bp22", "bp23", "bp24", "bp25",
    "bp31", "bp32", "bp33", "bp34", "bp35",
    "bp41", "bp42", "bp43", "bp44", "bp45",
    "bp51", "bp52", "bp53", "bp54", "bp55",
    # "bp111", "bp112", "bp113", "bp114", "bp115",
    # "bp121", "bp122", "bp123", "bp124", "bp125",
    # "bp131", "bp132", "bp133", "bp134", "bp135",
    # "bp141", "bp142", "bp143", "bp144", "bp145",
    # "bp151", "bp152", "bp153", "bp154", "bp155",
]
