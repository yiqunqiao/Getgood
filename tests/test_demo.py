import json
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
    # Construct a known answer without calling the presentation shortcut, so
    # these tests represent submissions without recorded demo assistance.
    folder=module.ROOT/'tasks'/task
    definition=json.loads((folder/'task.json').read_text())
    return {'task_id':task,
            'tests':(folder/f'demo_{kind}.py').read_text(),
            'judgements':definition['known_risks'] if kind=='good' else [],
            'consequence':definition['expected_consequence'] if kind=='good' else 'unrelated',
            'boundaries':{'seq_retry':'verified' if kind=='good' else 'unverified',
                          'new_request':'verified' if kind=='good' and task!='t1_refund' else 'unverified',
                          'concurrent':'unverified'}}

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
    assert client.get('/api/demo/t2_coupon/good').status_code==405
    client.headers.pop('X-GetGood-Token')
    assert client.post('/api/reset').status_code==403
    assert client.post('/api/demo/t2_coupon/good',json={}).status_code==403


def test_comparison_preserves_growth_and_promotion(client):
    client.post('/api/hint/t1_refund')
    client.post('/api/submit',json=example(client,'t1_refund'))
    client.post('/api/submit',json=example(client,'t2_coupon'))
    before=client.get('/api/progress').json()
    for kind in ['bad','good']:
        result=client.post('/api/compare',json=example(client,'t3_legit_refund',kind)).json()
        assert result['recorded'] is False
        assert result['success']==(kind=='good')
        assert result['level']==result['previous_level']=='Independent'
        after=client.get('/api/progress').json()
        assert after['level']==before['level']
        assert after['history']==before['history']
        assert after['assistance']['t3_legit_refund']['feedback_seen'] is True
    result=client.post('/api/submit',json=example(client,'t3_legit_refund')).json()
    assert result['previous_level']=='Independent'
    assert result['level']=='Independent'
    assert result['completion']=='Practice completed after feedback'
    assert len(client.get('/api/progress').json()['history'])==3


def test_risk_locations_and_boundary_history(client):
    for task in ['t1_refund','t2_coupon']:
        payload=example(client,task)
        payload['judgements'][0]['line']=1
        payload['boundaries']['concurrent']='need_mentor'
        result=client.post('/api/submit',json=payload).json()
        assert result['success'] and result['judgement']['correct']
        entry=client.get('/api/progress').json()['history'][-1]
        assert entry['boundary_claims']['concurrent']=='need_mentor'
        assert entry['result']['boundaries']['concurrent']=='need_mentor'
        assert entry['previous_level'] and entry['level_reason']
        payload['judgements'][0]['line']=2
        wrong=client.post('/api/compare',json=payload).json()
        assert wrong['judgement']['missed'] and wrong['judgement']['false_positive']
        payload['judgements'][0]={'line':1,'type':'precision'}
        assert not client.post('/api/compare',json=payload).json()['judgement']['correct']
    assert all('risk_locations' not in t for t in client.get('/api/tasks').json())


def test_guided_success_without_hints_does_not_promote(client):
    result=client.post('/api/submit',json=example(client,'t1_refund')).json()
    assert result['success']
    assert result['hints_used']==0
    assert result['previous_level']==result['level']=='Needs guidance'
    assert client.get('/api/progress').json()['history'][0]['independent'] is False
    transfer=client.post('/api/submit',json=example(client,'t2_coupon')).json()
    assert transfer['success'] and transfer['level']=='Independent'


def test_consequence_is_checked_without_revealing_answer(client):
    payload=example(client,'t1_refund')
    payload['consequence']='unrelated'
    result=client.post('/api/compare',json=payload).json()
    assert not result['success']
    assert result['judgement']['correct']
    assert result['consequence']=={'correct':False,'selected':'unrelated','expected':None}
    assert 'expected_consequence' not in client.get('/api/tasks').json()[0]
    assert client.get('/api/progress').json()['history']==[]


def test_corrupt_local_progress_uses_empty_state(client):
    module.DATA.mkdir(exist_ok=True)
    (module.DATA/'progress.json').write_text('{broken')
    assert client.get('/api/progress').json()=={'level':'Needs guidance','history':[],'hints':{},'assistance':{}}


def test_demo_shortcuts_are_server_recorded_and_survive_navigation_and_refresh(client):
    for task in ['t2_coupon','t3_legit_refund']:
        loaded=client.post(f'/api/demo/{task}/good',json={}).json()
        assert loaded['tests']
        assert client.get('/api/tasks').status_code==200  # switch away and back
        with TestClient(module.app) as refreshed:
            refreshed.headers['X-GetGood-Token']=client.headers['X-GetGood-Token']
            assert refreshed.get('/api/progress').json()['assistance'][task]['demo_used'] is True
            payload={'task_id':task,**loaded}
            payload['tests']+='\n# Edited after loading the example.\n'
            payload['demo_used']=False  # client-supplied flags cannot restore eligibility
            result=refreshed.post('/api/submit',json=payload).json()
        assert result['success'] and not result['independent']
        assert result['completion']=='Demonstration completed'
        assert result['level']=='Needs guidance'
    history=client.get('/api/progress').json()['history']
    assert all(not entry['independent'] for entry in history)


def test_bad_demo_shortcut_also_disqualifies_later_success(client):
    client.post('/api/demo/t2_coupon/bad',json={})
    result=client.post('/api/submit',json=example(client,'t2_coupon')).json()
    assert result['success'] and result['completion']=='Demonstration completed'
    assert result['level']=='Needs guidance'


def test_demo_after_independent_coupon_does_not_complete_cross_scenario_level(client):
    coupon=client.post('/api/submit',json=example(client,'t2_coupon')).json()
    assert coupon['independent'] and coupon['level']=='Independent'
    client.post('/api/demo/t3_legit_refund/good',json={})
    exception=client.post('/api/submit',json=example(client,'t3_legit_refund')).json()
    assert exception['success'] and not exception['independent']
    assert exception['completion']=='Demonstration completed'
    assert exception['level']=='Independent'


def test_feedback_marks_retries_as_practice_but_not_the_first_success(client):
    first=client.post('/api/submit',json=example(client,'t2_coupon')).json()
    assert first['independent'] and first['level']=='Independent'
    repeat=client.post('/api/submit',json=example(client,'t2_coupon')).json()
    assert repeat['success'] and not repeat['independent']
    assert repeat['completion']=='Practice completed after feedback'
    third=client.post('/api/submit',json=example(client,'t3_legit_refund')).json()
    assert third['independent'] and third['level']=='Verified across scenarios'


def test_feedback_comparison_before_first_submit_blocks_independent_credit(client):
    result=client.post('/api/compare',json=example(client,'t2_coupon')).json()
    assert result['success'] and client.get('/api/progress').json()['history']==[]
    later=client.post('/api/submit',json=example(client,'t2_coupon')).json()
    assert later['success'] and not later['independent']
    assert later['completion']=='Practice completed after feedback'
    assert later['level']=='Needs guidance'


def test_older_progress_with_a_submission_migrates_to_feedback_seen(client):
    client.post('/api/submit',json=example(client,'t2_coupon'))
    saved=json.loads((module.DATA/'progress.json').read_text())
    saved.pop('assistance')
    (module.DATA/'progress.json').write_text(json.dumps(saved))
    assert client.get('/api/progress').json()['assistance']['t2_coupon']['feedback_seen']
    repeat=client.post('/api/submit',json=example(client,'t2_coupon')).json()
    assert repeat['completion']=='Practice completed after feedback'
    assert not repeat['independent']
