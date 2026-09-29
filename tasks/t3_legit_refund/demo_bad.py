def test_new_request_same_amount_allowed(env):
    pay = env.make_payment(amount_cents=10_000)
    env.svc.refund(pay.id, 3_000, request_id="r-1")
    env.svc.refund(pay.id, 3_000, request_id="r-2")
    assert len(env.gateway.calls) == 1
    assert env.db.get_payment(pay.id).refunded_cents == 3_000
