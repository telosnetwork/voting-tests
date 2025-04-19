# One of the nodes is configured to produce for 60 producers named "bp[1-60]"
from leap.errors import ChainAPIError

def bp_voting(cleos, native_account, first_address, second_address, erc20_contract, stlos_contract, manager_contract):
    """
    Test the voting process for block producers.
    """
    print("\nStarting BP voting test...")
    create_and_register(cleos)

def create_and_register(cleos):
    signing_key = 'EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L'
    for i in range(60):
        bp_name = f"bp{i + 1}"
        print(f"Creating and registering {bp_name}...")

        try:
            account = cleos.get_account(bp_name)
            print(f"Account {bp_name} already exists, skipping create...")
        except ChainAPIError as e:
            cleos.new_account(bp_name)

        cleos.register_producer(bp_name, signing_key)
