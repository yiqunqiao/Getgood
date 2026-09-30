from pathlib import Path
from typing import Literal
import json
import secrets
from datetime import datetime, timezone
from threading import Lock
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .grader import evaluate, run_tests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
LOCK=Lock()
TOKEN=secrets.token_urlsafe(32)
app=FastAPI(title='GetGood local demo')

class Judgement(BaseModel):
    line: int = Field(ge=1,le=1000)
    type: Literal['duplicate','precision','over_limit','concurrent','state','other']
class Submission(BaseModel):
    task_id: str
    tests: str = Field(min_length=1,max_length=20000)
    judgements: list[Judgement] = Field(default_factory=list,max_length=20)
    boundaries: dict[str,Literal['verified','unverified','need_mentor']] = Field(default_factory=dict)
    consequence: Literal['duplicate_effect','legitimate_request','unrelated'] | None = None

@app.middleware('http')
async def local_only(request: Request, call_next):
    if request.method=='POST' and request.headers.get('X-GetGood-Token')!=TOKEN:
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'Local session token required. Refresh the demo page.'},status_code=403)
    return await call_next(request)

def task_for(task_id):
    # Explicit allowlist prevents path traversal.
    if task_id not in ['t1_refund','t2_coupon','t3_legit_refund']:
        raise HTTPException(404,'Unknown task')
    return json.loads((ROOT/'tasks'/task_id/'task.json').read_text())

def state():
    if (DATA/'progress.json').exists():
        try:
            saved=json.loads((DATA/'progress.json').read_text())
            if (isinstance(saved,dict) and saved.get('level') in
                    ['Needs guidance','Independent','Verified across scenarios'] and
                    isinstance(saved.get('history'),list) and isinstance(saved.get('hints'),dict)):
                if not isinstance(saved.get('assistance'),dict):
                    saved['assistance']={}
                # Older progress files predate assistance tracking. A recorded
                # submission has already exposed detailed feedback for that task.
                for entry in saved['history']:
                    if isinstance(entry,dict) and entry.get('task_id') in ['t1_refund','t2_coupon','t3_legit_refund']:
                        saved['assistance'].setdefault(
                            entry['task_id'],{'demo_used':False,'feedback_seen':True})
                return saved
        except (OSError,UnicodeError,json.JSONDecodeError):
            pass
    return dict(level='Needs guidance',history=[],hints={},assistance={})

def assistance_for(progress,task_id):
    return progress.setdefault('assistance',{}).setdefault(
        task_id,{'demo_used':False,'feedback_seen':False})

def save(value):
    DATA.mkdir(exist_ok=True)
    temp=DATA/'progress.tmp'
    temp.write_text(json.dumps(value,indent=2))
    temp.replace(DATA/'progress.json')

@app.get('/api/session')
def session(): return {'token':TOKEN}

@app.get('/api/tasks')
def tasks():
    result=[]
    for id in ['t1_refund','t2_coupon','t3_legit_refund']:
        task=task_for(id)
        public={k:v for k,v in task.items() if k not in ['known_risks','risk_locations','required_variants','hints','boundaries','expected_consequence']}
        public['boundaries']=[{k:v for k,v in b.items() if k!='variants'} for b in task['boundaries']]
        public['code']=(ROOT/'tasks'/id/'shown.py').read_text()
        result.append(public)
    return result

@app.get('/api/progress')
def progress():
    with LOCK: return state()

@app.post('/api/reset')
def reset():
    with LOCK: save(dict(level='Needs guidance',history=[],hints={},assistance={}))
    return {'ok':True}

@app.post('/api/hint/{task_id}')
def hint(task_id:str):
    task=task_for(task_id)
    if not task['hints']: raise HTTPException(400,'No hints in this stage')
    with LOCK:
        s=state(); used=min(s['hints'].get(task_id,0)+1,len(task['hints']))
        s['hints'][task_id]=used; save(s)
    return dict(used=used,text=task['hints'][used-1])

@app.post('/api/demo/{task_id}/{kind}')
def demo(task_id:str,kind:Literal['good','bad']):
    task=task_for(task_id)
    tests=(ROOT/'tasks'/task_id/f'demo_{kind}.py').read_text()
    with LOCK:
        progress=state()
        assistance_for(progress,task_id)['demo_used']=True
        save(progress)
    return dict(tests=tests,
        judgements=task['known_risks'] if kind=='good' else [],
        consequence=task['expected_consequence'] if kind=='good' else 'unrelated',
        boundaries={'seq_retry':'verified' if kind=='good' else 'unverified',
                    'new_request':'verified' if kind=='good' and task_id!='t1_refund' else 'unverified',
                    'concurrent':'unverified'})

@app.post('/api/run')
def run(submission:Submission):
    task_for(submission.task_id)
    return run_tests(submission.task_id,'reference',submission.tests)

def evidence_reason(result, completion):
    if result['success']:
        return ('Required variants caught, legitimate reference behaviour accepted, and verified boundary claims supported. '
                + completion+'.')
    reasons=[]
    if result['judgement']['missed']: reasons.append('A risk was missed.')
    if result['judgement']['false_positive']: reasons.append('A risk judgement was not supported.')
    if not result['consequence']['correct'] and not result['judgement']['missed']:
        reasons.append('The consequence judgement needs revision.')
    if result['reference']['status']=='failed': reasons.append('Tests rejected legitimate reference behaviour.')
    elif result['reference']['status']!='passed': reasons.append('Tests could not establish valid evidence.')
    elif not all(v['caught'] for v in result['variants'].values()): reasons.append('Required behavioural evidence is incomplete.')
    if 'unsupported' in result['boundaries'].values(): reasons.append('A verified boundary claim lacks evidence.')
    return ' '.join(reasons)

@app.post('/api/compare')
def compare(submission:Submission):
    task=task_for(submission.task_id)
    with LOCK:
        result=evaluate(task,submission.model_dump())
        s=state(); used=s['hints'].get(task['id'],0)
        assistance_for(s,task['id'])['feedback_seen']=True
        save(s)
    return {**result,'recorded':False,'hints_used':used,'previous_level':s['level'],
            'level':s['level'],'completion':'Comparison only',
            'reason':evidence_reason(result,'Comparison completed'),
            'level_reason':'Comparison does not change the level or submission history. Later attempts on this exercise count as practice after feedback.'}

@app.post('/api/submit')
def submit(submission:Submission):
    task=task_for(submission.task_id)
    # Serialize local demo submissions and history updates.
    with LOCK:
        result=evaluate(task,submission.model_dump())
        s=state(); used=s['hints'].get(task['id'],0)
        assistance=assistance_for(s,task['id']).copy()
        independent=(result['success'] and used==0 and task['stage']!='Guided'
                     and not assistance['demo_used'] and not assistance['feedback_seen'])
        completion=('Needs revision' if not result['success'] else
                    'Demonstration completed' if assistance['demo_used'] else
                    'Guided practice completed' if task['stage']=='Guided' else
                    'Practice completed after feedback' if assistance['feedback_seen'] else
                    'Practice completed with hints' if used else
                    'Completed without recorded assistance')
        old=s['level']
        levels=['Needs guidance','Independent','Verified across scenarios']
        if result['success']:
            if independent:
                s['level']=levels[max(1,levels.index(old))]
                previous={entry['task_id'] for entry in s['history'] if entry['independent']}
                previous.add(task['id'])
                # Coupon and the independent refund exception are two business contexts.
                if {'t2_coupon','t3_legit_refund'}<=previous: s['level']=levels[2]
        else:
            s['level']=levels[max(0,levels.index(old)-1)]
        reason=evidence_reason(result,completion)
        if not result['success']:
            level_reason='Unsuccessful recorded submission lowers the level by one, to a minimum of Needs guidance.'
        elif s['level']=='Verified across scenarios':
            level_reason='Independent evidence exists for both the coupon scenario and the legitimate refund exception.'
        elif independent:
            level_reason='Successful evidence without hints establishes independent performance.'
        elif assistance['demo_used']:
            level_reason='A presentation example was loaded for this exercise. The result is recorded as a demonstration, not independent evidence.'
        elif task['stage']=='Guided':
            level_reason='Guided practice adds evidence but does not raise the independent level.'
        elif used:
            level_reason='Hints were used for this exercise. The pass adds practice evidence but does not raise the independent level.'
        else:
            level_reason='Earlier detailed feedback was shown for this exercise. This pass counts as practice, not independent evidence.'
        entry=dict(task_id=task['id'],title=task['title'],time=datetime.now(timezone.utc).isoformat(),
            independent=independent,completion=completion,assistance=assistance,
            hints_used=used,previous_level=old,level=s['level'],reason=reason,
            level_reason=level_reason,result=result,boundary_claims=submission.boundaries)
        s['history'].append(entry)
        assistance_for(s,task['id'])['feedback_seen']=True
        save(s)
    return {**result,'recorded':True,'hints_used':used,'previous_level':old,'level':s['level'],
            'independent':independent,'completion':completion,'reason':reason,'level_reason':level_reason}

@app.get('/')
def home(): return FileResponse(ROOT/'frontend/index.html')

app.mount('/static',StaticFiles(directory=ROOT/'frontend'),name='static')
