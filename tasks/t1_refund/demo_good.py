def test_retry_refunds_once(env):
    pay = env.make_payment(amount_cents=10_000)
    env.svc.refund(pay.id, 3_000, request_id="r-1")
    env.svc.refund(pay.id, 3_000, request_id="r-1")
    assert len(env.gateway.calls) == 1
