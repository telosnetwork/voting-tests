# One of the nodes is configured to produce for 60 producers named "bp[1-60]"
from leap.errors import ChainAPIError

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
    sync_bp_status(cleos)

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

def sync_bp_status(cleos):
    return
    # TODO: Implement the action on eosio contract to sync the active/inactive status of a specific block producer
    #  into the EVM.
    #
    #  Then call that action for each producer here, so all producers are synced.
    #
    #  Then unregister a producer, sync it and check that the status is updated in the EVM.
