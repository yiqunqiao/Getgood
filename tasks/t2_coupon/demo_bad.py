def test_first_operation(env):
    campaign = env.make_campaign(remaining=5)
    env.svc.claim_coupon("u-1", campaign.id, request_id="r-1")
    assert len(env.wallet.calls) == 1
