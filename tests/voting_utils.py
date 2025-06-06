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

def get_native_account_vote_weight(cleos, voter):
    voter = cleos.get_table(
        'eosio', 'eosio', 'voters',
        lower_bound=voter,
        upper_bound=voter
    )
    return int(float(voter[0]['last_vote_weight'])) * 10**14 if voter and len(voter) > 0 else 0

def get_evm_account_vote_weight(cleos, manager_contract, address):
    user_vote = manager_contract.functions.userVotes(address).call()
    if user_vote:
        vote_weight = user_vote[0]
    else:
        vote_weight = 0

    cleos.logger.info(f"EVM account {address} has vote weight: {vote_weight}")
    return vote_weight  # in wei (10^18 units) for consistency with EVM calculations

def assert_bp_voteweight(cleos, manager_contract, producer_names, vote_weight):
    vote_weight_wei = int(vote_weight * 10**18)
    # Set threshold to handle decay calculation differences - about 0.1% should be sufficient
    threshold = int(vote_weight_wei * 0.001)  # 0.1% tolerance

    for producer in producer_names:
        evm_vote_weight = manager_contract.functions.totalVotes(s2n(producer)).call()
        native_producer = cleos.get_producer(producer)
        native_vote_weight = int(0)
        if native_producer:
            native_vote_weight = int(float(native_producer['total_votes'])) * 10**14

        # Debug output to verify values
        print(f"Debug {producer}:")
        print(f"  Vote weight input: {vote_weight}")
        print(f"  Expected: {vote_weight_wei}")
        print(f"  EVM:      {evm_vote_weight}")
        print(f"  Native:   {native_vote_weight}")

        # Safe percentage calculation
        evm_diff_abs = abs(evm_vote_weight - vote_weight_wei)
        if vote_weight_wei > 0:
            evm_diff_pct = evm_diff_abs / vote_weight_wei * 100
            print(f"  EVM diff: {evm_diff_abs} ({evm_diff_pct:.4f}%)")
        else:
            print(f"  EVM diff: {evm_diff_abs} (undefined % - expected vote weight is 0)")
            # If expected is 0, check if actual is also close to 0
            assert evm_vote_weight == 0, f"Expected vote weight is 0 but EVM shows {evm_vote_weight}"
            assert native_vote_weight == 0, f"Expected vote weight is 0 but Native shows {native_vote_weight}"
            continue  # Skip the normal threshold checks

        # Check EVM vote weight with threshold
        evm_diff = abs(evm_vote_weight - vote_weight_wei)
        assert evm_diff <= threshold, f"EVM vote weight for {producer} is {evm_vote_weight}, expected {vote_weight_wei} ± {threshold}, difference: {evm_diff} ({evm_diff / vote_weight_wei * 100:.4f}%)"

        # Check native vote weight with threshold
        native_diff = abs(native_vote_weight - vote_weight_wei)
        assert native_diff <= threshold, f"Native vote weight for {producer} is {native_vote_weight}, expected {vote_weight_wei} ± {threshold}, difference: {native_diff} ({native_diff / vote_weight_wei * 100:.4f}%)"

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
