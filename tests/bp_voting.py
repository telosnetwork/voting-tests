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

def create_and_register(cleos):
    signing_key = 'EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L'
    for bp_name in producers:
        print(f"Creating and registering {bp_name}...")

        try:
            account = cleos.get_account(bp_name)
            print(f"Account {bp_name} already exists, skipping create...")
        except ChainAPIError as e:
            cleos.new_account(bp_name)

        cleos.register_producer(bp_name, signing_key)
