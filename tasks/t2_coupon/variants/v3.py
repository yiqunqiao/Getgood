def claim_coupon(user_id, campaign_id, request_id):
    key = (campaign_id, user_id)
    if key in requests:
        return requests[key]
    c = db.get_campaign(campaign_id)
    if c.remaining <= 0:
        raise SoldOut()
    wallet.add(user_id, campaign_id)
    c.remaining -= 1
    db.save(c)
    result = {"user_id": user_id, "remaining": c.remaining}
    requests[key] = result
    return result
