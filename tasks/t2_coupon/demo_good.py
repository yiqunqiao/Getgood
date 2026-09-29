def test_retry_claims_once(env):
    campaign = env.make_campaign(remaining=5)
    env.svc.claim_coupon("u-1", campaign.id, request_id="r-1")
    env.svc.claim_coupon("u-1", campaign.id, request_id="r-1")
    assert len(env.wallet.calls) == 1
    assert env.db.get_campaign(campaign.id).remaining == 4

def test_new_claim_allowed(env):
    campaign = env.make_campaign(remaining=5)
    env.svc.claim_coupon("u-1", campaign.id, request_id="r-1")
    env.svc.claim_coupon("u-1", campaign.id, request_id="r-2")
    assert len(env.wallet.calls) == 2
