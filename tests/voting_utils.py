from tevmtest import DEFAULT_GAS_PRICE


def stake_erc20(cleos, eth_address, erc20_contract, stlos_contract, manager_contract, amount):
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

def vote_evm(cleos, address, manager_contract, producer_names):
    before_first_bp_votes = manager_contract.functions.totalVotes(producer_names[0]).call()
    cleos.logger.info(f"Making vote for {address}...")
    vote_receipt = cleos.eth_build_and_send_transaction(
        # manager_contract.functions.vote(sorted(producer_names)),
        manager_contract.functions.vote([producer_names[0]]),
        address,
        4000000,
        DEFAULT_GAS_PRICE
    )
    after_first_bp_votes = manager_contract.functions.totalVotes(producer_names[0]).call()
    assert before_first_bp_votes < after_first_bp_votes
    cleos.logger.info(f"Vote receipt: {vote_receipt}")

def vote_native(cleos, account, producer_names):
    cleos.logger.info(f"Making vote for {account}...")
    cleos.vote_producers(account, None, producer_names);
    cleos.logger.info(f"Vote complete for {account}")

