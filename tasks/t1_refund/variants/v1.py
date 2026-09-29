def refund(payment_id, amount_cents, request_id):
    p = db.get_payment(payment_id)
    if p.status != "SUCCEEDED":
        raise RefundError("payment not refundable")
    if amount_cents <= 0 or p.refunded_cents + amount_cents > p.amount_cents:
        raise RefundError("invalid refund amount")
    gateway.refund(p.id, amount_cents)
    p.refunded_cents += amount_cents
    db.save(p)
    return {"refund_id": new_id(), "refunded_cents": p.refunded_cents}
