# One of the nodes is configured to produce for 60 producers named "bp[1-60]"
from time import sleep

from antelope_rs.antelope_rs import Name
from leap.errors import ChainAPIError
from eth_account import Account

from setup import DEFAULT_GAS_PRICE
from tevmtest import to_wei
from eth_abi import encode

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
    print("\nStarting BP voting test...")
    create_and_register(cleos)
    register_bps_evm(cleos, first_address, manager_contract)
    sleep(1)
    do_evm_voting(cleos, first_address, second_address, erc20_contract, stlos_contract, manager_contract)

def create_and_register(cleos):
    for bp_name in producers:
        print(f"Creating and registering {bp_name}...")

        try:
            cleos.get_account(bp_name)
            print(f"Account {bp_name} already exists, skipping create...")

        except ChainAPIError:
            cleos.new_account(bp_name, key=cleos.keys['eosio'])
            print(f"Account {bp_name} created")

        cleos.register_producer(
            bp_name,
            pub_key=cleos.keys['eosio'],
            key=cleos.private_keys['eosio'],
        )
        print(f"BP {bp_name} registered")

def register_bps_evm(cleos, deployer_addr, manager_contract):
    for producer in producers:
        register_bp_evm(cleos, deployer_addr, manager_contract, producer)

def register_bp_evm(cleos, deployer_addr, manager_contract, producer):
    producer_name = Name.from_str(producer)
    producer_u64 = producer_name.value()
    register_bp_fn = manager_contract.functions.registerBP(producer_u64)
    register_bp_receipt = cleos.eth_build_and_send_transaction(register_bp_fn, deployer_addr, 100000, DEFAULT_GAS_PRICE)
    is_active = manager_contract.functions.activeBPs(producer_u64).call()
    if not is_active:
        raise Exception(f"Producer {producer} is not active after registration")

    print(f"Registered {producer} to EVM")
    # TODO: Implement the action on eosio contract to sync the active/inactive status of a specific block producer
    #  into the EVM.
    #
    #  Then call that action for each producer here, so all producers are synced.
    #
    #  Then unregister a producer, sync it and check that the status is updated in the EVM.

def do_evm_voting(cleos, first_address, second_address, erc20_contract, stlos_contract, manager_contract):
    stake_erc20(cleos, first_address, erc20_contract, stlos_contract, manager_contract, to_wei(1000, 'ether'))
    print(f"Staked 1000 STLOS for {first_address}")
    # vote_fn = manager_contract.functions.vote()

def stake_erc20(cleos, eth_address, erc20_contract, stlos_contract, manager_contract, amount):
    starting_stlos_balance = stlos_contract.functions.balanceOf(eth_address.address).call()
    print(f"Starting STLOS balance for {eth_address.address}: {starting_stlos_balance}")

    approve_fn = erc20_contract.functions.approve(stlos_contract.address, amount)
    approve_receipt = cleos.eth_build_and_send_transaction(approve_fn, eth_address, 100000, DEFAULT_GAS_PRICE)
    print(f"Approved {amount} STLOS balance for {eth_address.address}")

    deposit_fn = stlos_contract.functions.deposit(amount, eth_address.address)
    deposit_receipt = cleos.eth_build_and_send_transaction(deposit_fn, eth_address, 200000, DEFAULT_GAS_PRICE)

    ending_stlos_balance = stlos_contract.functions.balanceOf(eth_address.address).call()
    print(f"Minted {amount} STLOS for {eth_address.address}, ending balance is {ending_stlos_balance}")

    approve_stlos_fn = stlos_contract.functions.approve(manager_contract.address, amount)
    approve_stlos_receipt = cleos.eth_build_and_send_transaction(approve_stlos_fn, eth_address, 100000, DEFAULT_GAS_PRICE)

    stake_fn = manager_contract.functions.stake(amount)
    stake_receipt = cleos.eth_build_and_send_transaction(stake_fn, eth_address, 200000, DEFAULT_GAS_PRICE)

    staked_balance = manager_contract.functions.userStakedBalance(eth_address.address).call()
    print(f"Staked {amount} STLOS for {eth_address.address}, staked balance is {staked_balance}")
