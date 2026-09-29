import pytest
from fastapi.testclient import TestClient
import backend.app as module
from backend.grader import run_tests

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'DATA',tmp_path)
    with TestClient(module.app) as c:
        c.headers['X-GetGood-Token']=c.get('/api/session').json()['token']
        yield c

def example(client,task,kind='good'):
    return {'task_id':task,**client.get(f'/api/demo/{task}/{kind}').json()}

def test_three_act_story_and_regression(client):
    first='t1_refund'
    bad=client.post('/api/submit',json=example(client,first,'bad')).json()
    assert not bad['success'] and bad['judgement']['missed']
    client.post('/api/hint/'+first)
    client.post('/api/hint/'+first)
    guided=client.post('/api/submit',json=example(client,first)).json()
    assert guided['success'] and guided['hints_used']==2
    assert guided['level']=='Needs guidance'
    second=client.post('/api/submit',json=example(client,'t2_coupon')).json()
    assert second['success'] and second['level']=='Independent'
    third=client.post('/api/submit',json=example(client,'t3_legit_refund')).json()
    assert third['success'] and third['level']=='Verified across scenarios'
    bad=client.post('/api/submit',json=example(client,'t3_legit_refund','bad')).json()
    assert bad['reference']['status']=='failed' and not bad['success']
    assert bad['level']=='Independent'
    assert len(client.get('/api/progress').json()['history'])==5

def test_invalid_tests_are_not_evidence(client):
    payload=example(client,'t1_refund')
    for code in ['def invalid(', 'x = 1', 'def test_error(env):\n    raise ValueError("broken test")', 'import pytest\n@pytest.mark.skip\ndef test_skipped():\n    pass']:
        payload['tests']=code
        result=client.post('/api/submit',json=payload).json()
        assert result['reference']['status']=='error'
        assert not any(v['caught'] for v in result['variants'].values())

def test_boundary_and_false_positive(client):
    payload=example(client,'t3_legit_refund')
    payload['boundaries']['concurrent']='verified'
    result=client.post('/api/submit',json=payload).json()
    assert not result['success'] and result['boundaries']['concurrent']=='unsupported'
    payload=example(client,'t3_legit_refund')
    payload['judgements']=[{'type':'duplicate','line':7}]
    result=client.post('/api/submit',json=payload).json()
    assert not result['success'] and result['judgement']['false_positive']

def test_timeout():
    result=run_tests('t1_refund','reference','def test_loop():\n    while True:\n        pass',timeout=.5)
    assert result['status']=='timeout'

def test_public_api_and_token(client):
    tasks=client.get('/api/tasks').json()
    assert len(tasks)==3 and 'known_risks' not in tasks[0]
    assert 'variants' not in tasks[0]['boundaries'][0]
    assert client.post('/api/hint/t2_coupon').status_code==400
    assert client.get('/').status_code==200
    assert client.get('/static/style.css').status_code==200
    client.headers.pop('X-GetGood-Token')
    assert client.post('/api/reset').status_code==403
