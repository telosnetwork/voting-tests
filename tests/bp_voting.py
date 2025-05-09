# One of the nodes is configured to produce for 60 producers named "bp[1-60]"
from time import sleep

from antelope_rs.antelope_rs import Name
from leap.errors import ChainAPIError

from setup import DEFAULT_GAS_PRICE
from decay import check_decay
from tests.voting_utils import stake_erc20, vote_evm
from tevmtest import to_wei

from tevmtest.utils import s2n

producers = [
    "bp1",  "bp2",  "bp3",  "bp4",  "bp5",
    "bp11", "bp12", "bp13", "bp14", "bp15",
    "bp21", "bp22", "bp23", "bp24", "bp25",
    "bp31", "bp32", "bp33", "bp34", "bp35",
    "bp41", "bp42", "bp43", "bp44", "bp45",
    "bp51", "bp52", "bp53", "bp54", "bp55",
    "bp111", "bp112", "bp113", "bp114", "bp115",
    "bp121", "bp122", "bp123", "bp124", "bp125",
    "bp131", "bp132", "bp133", "bp134", "bp135",
    "bp141", "bp142", "bp143", "bp144", "bp145",
    "bp151", "bp152", "bp153", "bp154", "bp155",
]

def bp_voting(cleos, native_account, first_address, second_address, erc20_contract, stlos_contract, manager_contract):
    """
    Test the voting process for block producers.
    """
    cleos.logger.info("\nStarting BP voting test...")
    create_and_register(cleos)
    register_bps_evm(cleos, first_address, manager_contract)
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

def register_bps_evm(cleos, deployer_addr, manager_contract):
    for producer in producers:
        register_bp_evm(cleos, deployer_addr, manager_contract, producer)

def register_bp_evm(cleos, deployer_addr, manager_contract, producer):
    cleos.logger.info(f"Registering {producer} to EVM...")
    producer_name = Name.from_str(producer)
    producer_u64 = producer_name.value()
    register_bp_fn = manager_contract.functions.registerBP(producer_u64)
    register_bp_receipt = cleos.eth_build_and_send_transaction(register_bp_fn, deployer_addr, 100000, DEFAULT_GAS_PRICE)
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
    cleos.logger.info("\nStarting EVM voting...")
    stake_erc20(cleos, first_address, erc20_contract, stlos_contract, manager_contract, to_wei(1000, 'ether'))
    cleos.logger.info(f"Staked 1000 STLOS for {first_address}")
    vote_evm(cleos, first_address, manager_contract, [s2n(x) for x in producers[:30]])
    cleos.logger.info(f"Voted with {first_address} for producers: {producers[:30]}")
    for producer in producers[:30]:
        vote_weight = manager_contract.functions.totalVotes(s2n(producer)).call()
        assert vote_weight > 0, f"Vote weight for {producer} is 0 after voting"

    # TODO: Increase value of STLOS, refresh vote and check that the vote weight is updated

    vote_evm(cleos, first_address, manager_contract, [])

