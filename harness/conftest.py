from types import SimpleNamespace
from copy import deepcopy
import pytest
import svc

class Database:
    def __init__(self):
        self.items = {}
    def get_payment(self, key):
        return deepcopy(self.items[key])
    def get_campaign(self, key):
        return deepcopy(self.items[key])
    def save(self, item):
        self.items[item.id] = deepcopy(item)

class Recorder:
    def __init__(self):
        self.calls = []
    def refund(self, *args):
        self.calls.append(args)
    def add(self, *args):
        self.calls.append(args)

class RefundError(Exception):
    pass
class SoldOut(Exception):
    pass

@pytest.fixture
def env():
    db, gateway, wallet = Database(), Recorder(), Recorder()
    svc.db, svc.gateway, svc.wallet = db, gateway, wallet
    svc.requests = {}
    svc.RefundError, svc.SoldOut = RefundError, SoldOut
    counter = iter(range(1, 10000))
    svc.new_id = lambda: str(next(counter))
    def make_payment(amount_cents=10000):
        p = SimpleNamespace(id='p-' + svc.new_id(), amount_cents=amount_cents,
                            refunded_cents=0, status='SUCCEEDED')
        db.save(p)
        return p
    def make_campaign(remaining=10):
        c = SimpleNamespace(id='c-' + svc.new_id(), remaining=remaining)
        db.save(c)
        return c
    return SimpleNamespace(svc=svc, db=db, gateway=gateway, wallet=wallet,
        make_payment=make_payment, make_campaign=make_campaign)
