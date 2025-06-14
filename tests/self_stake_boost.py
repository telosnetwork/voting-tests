from antelope_rs.antelope_rs import Asset
from voting_utils import vote_native, producers, assert_bp_voteweight, get_native_account_vote_weight


def check_self_stake_boost(cleos, native_funder, manager_contract):
    amount = 1_000_000
    producer_names = producers[:30]
    assert_bp_voteweight(cleos, manager_contract, producer_names, 0)

    # Transfer some TLOS to a BP
    native_amount = amount - 20
    quantity = Asset.from_str(f"{native_amount}.0000 TLOS")
    cleos.transfer_token(native_funder, producer_names[0], quantity, 'evm test')

    # Stake TLOS on native side to vote with
    half_amount = str(native_amount / 2).split('.')[0]
    resource_amount = Asset.from_str(f"{half_amount}.0000 TLOS")
    cleos.delegate_bandwidth(producer_names[0], producer_names[0], resource_amount, resource_amount, False)

    # Vote to BPs including itself
    vote_native(cleos, producer_names[0], producer_names)
    cleos.logger.info(f"Voted with {producer_names[0]} for producers: {producer_names}")

    # Get its vote weight
    vote_weight = get_native_account_vote_weight(cleos, producer_names[0]) / 10**14

    # Set threshold to handle calculation differences - about 0.1% should be sufficient
    threshold = int(vote_weight * 0.001)  # 0.1% tolerance

    # Get the total votes of itself and check that it is boosted by 10x
    self_stake_boost_multiplier = 10
    self_producer = cleos.get_producer(producer_names[0])
    self_total_votes = int(0)
    if self_producer:
        self_total_votes = int(float(self_producer['total_votes']))
    assert abs(self_total_votes - vote_weight * (1 + self_stake_boost_multiplier)) <= threshold

    # Get the total votes of other BPs and check that they are not boosted
    for producer in producer_names[1:]:
        other_producer = cleos.get_producer(producer)
        other_total_votes = int(0)
        if other_producer:
            other_total_votes = int(float(other_producer['total_votes']))
        assert abs(other_total_votes - vote_weight) <= threshold

    # Reset votes to 0
    vote_native(cleos, producer_names[0], [])
    assert_bp_voteweight(cleos, manager_contract, producer_names, 0)
