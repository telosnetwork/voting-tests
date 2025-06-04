# One of the nodes is configured to produce for 60 producers named "bp[1-60]"
from time import sleep

from antelope_rs.antelope_rs import Name
from leap.errors import ChainAPIError

from decay import check_decay
from voting_utils import deposit_and_stake_erc20, vote_evm, producers, unstake_erc20
from tevmtest import to_wei

from tevmtest.utils import s2n

def bp_voting(cleos, native_account, first_address, second_address, erc20_contract, stlos_contract, manager_contract):
    """
    Test the voting process for block producers.
    """
    cleos.logger.info("\nStarting BP voting test...")
    create_and_register(cleos)
    register_bps_evm(cleos, native_account, first_address, manager_contract)
    sleep(1)
    do_evm_voting(cleos, first_address, second_address, erc20_contract, stlos_contract, manager_contract)
    check_decay(cleos, native_account, first_address, erc20_contract, stlos_contract, manager_contract)

def create_and_register(cleos):
    for bp_name in producers:
        cleos.logger.info(f"Creating and registering {bp_name}...")

        try:
            cleos.get_account(bp_name)
            cleos.logger.info(f"Account {bp_name} already exists, skipping create...")

        except ChainAPIError:
            cleos.new_account(bp_name, key=cleos.keys['eosio'])
            cleos.logger.info(f"Account {bp_name} created")

        cleos.register_producer(
            bp_name,
            pub_key=cleos.keys['eosio'],
            key=cleos.private_keys['eosio'],
        )
        cleos.logger.info(f"BP {bp_name} registered")

def register_bps_evm(cleos, native_account, deployer_addr, manager_contract):
    for producer in producers:
        register_bp_evm(cleos, native_account, deployer_addr, manager_contract, producer)

def register_bp_evm(cleos, native_account, deployer_addr, manager_contract, producer):
    cleos.logger.info(f"Registering {producer} to EVM...")
    producer_name = Name.from_str(producer)
    producer_u64 = producer_name.value()
    # register_bp_fn = manager_contract.functions.registerBP(producer_u64)
    # register_bp_receipt = cleos.eth_build_and_send_transaction(register_bp_fn, deployer_addr, 100000, DEFAULT_GAS_PRICE)
    sync_bp_result = cleos.push_action(
        'eosio',
        'setbpevmstat',
        [producer_name],
        actor=native_account,
        key=cleos.get_private_key(native_account),
    )
    sleep(1)

    is_active = manager_contract.functions.activeBPs(producer_u64).call()
    if not is_active:
        raise Exception(f"Producer {producer} is not active after registration")

    cleos.logger.info(f"Registered {producer} to EVM")
    # TODO: Implement the action on eosio contract to sync the active/inactive status of a specific block producer
    #  into the EVM.
    #
    #  Then call that action for each producer here, so all producers are synced.
    #
    #  Then unregister a producer, sync it and check that the status is updated in the EVM.

def do_evm_voting(cleos, first_address, second_address, erc20_contract, stlos_contract, manager_contract):
    vote_amount_eth = 1_000_000;
    cleos.logger.info("\nStarting EVM voting...")
    deposit_and_stake_erc20(cleos, first_address, erc20_contract, stlos_contract, manager_contract, to_wei(vote_amount_eth, 'ether'))
    cleos.logger.info(f"Staked 1000 STLOS for {first_address}")
    vote_evm(cleos, first_address, manager_contract, [s2n(x) for x in producers[:30]])
    cleos.logger.info(f"Voted with {first_address} for producers: {producers[:30]}")
    for producer in producers[:30]:
        vote_weight = manager_contract.functions.totalVotes(s2n(producer)).call()
        assert vote_weight > 0, f"Vote weight for {producer} is 0 after voting"

    # TODO: Increase value of STLOS, refresh vote and check that the vote weight is updated

    vote_evm(cleos, first_address, manager_contract, [])

    for producer in producers[:30]:
        vote_weight = manager_contract.functions.totalVotes(s2n(producer)).call()
        assert vote_weight == 0, f"Vote weight for {producer} is not 0 after voting"

    unstake_erc20(cleos, first_address, erc20_contract, stlos_contract, manager_contract, to_wei(vote_amount_eth, 'ether'))
    cleos.logger.info(f"Unstaked 1000 STLOS for {first_address}")
    stake_weight = manager_contract.functions.userStakedBalance(first_address.address).call()
    assert stake_weight == 0, f"Stake weight for {first_address} is not 0 after unstaking"

    user_vote = manager_contract.functions.userVotes(first_address.address).call()
    assert user_vote[0] == 0, f"Vote weight for {first_address} is not 0 after voting for []"
    assert user_vote[1] == 0, f"BP count for {first_address} is not 0 after voting for []"
