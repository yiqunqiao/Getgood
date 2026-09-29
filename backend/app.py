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
    if (DATA/'progress.json').exists(): return json.loads((DATA/'progress.json').read_text())
    return dict(level='Needs guidance',history=[],hints={})

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
        public={k:v for k,v in task.items() if k not in ['known_risks','required_variants','hints','boundaries']}
        public['boundaries']=[{k:v for k,v in b.items() if k!='variants'} for b in task['boundaries']]
        public['code']=(ROOT/'tasks'/id/'shown.py').read_text()
        result.append(public)
    return result

@app.get('/api/progress')
def progress():
    with LOCK: return state()

@app.post('/api/reset')
def reset():
    with LOCK: save(dict(level='Needs guidance',history=[],hints={}))
    return {'ok':True}

@app.post('/api/hint/{task_id}')
def hint(task_id:str):
    task=task_for(task_id)
    if not task['hints']: raise HTTPException(400,'No hints in this stage')
    with LOCK:
        s=state(); used=min(s['hints'].get(task_id,0)+1,len(task['hints']))
        s['hints'][task_id]=used; save(s)
    return dict(used=used,text=task['hints'][used-1])

@app.get('/api/demo/{task_id}/{kind}')
def demo(task_id:str,kind:Literal['good','bad']):
    task=task_for(task_id)
    return dict(tests=(ROOT/'tasks'/task_id/f'demo_{kind}.py').read_text(),
        judgements=task['known_risks'] if kind=='good' else [],
        boundaries={'seq_retry':'verified' if kind=='good' else 'unverified',
                    'new_request':'verified' if kind=='good' and task_id!='t1_refund' else 'unverified',
                    'concurrent':'unverified'})

@app.post('/api/run')
def run(submission:Submission):
    task_for(submission.task_id)
    return run_tests(submission.task_id,'reference',submission.tests)

@app.post('/api/submit')
def submit(submission:Submission):
    task=task_for(submission.task_id)
    # Serialize local demo submissions and history updates.
    with LOCK:
        result=evaluate(task,submission.model_dump())
        s=state(); used=s['hints'].get(task['id'],0)
        independent=result['success'] and used==0
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
        reason=('Passed without hints.' if independent else 'Passed with guidance.' if result['success'] else 'More evidence or a corrected judgement is needed.')
        entry=dict(task_id=task['id'],title=task['title'],time=datetime.now(timezone.utc).isoformat(),
            independent=independent,hints_used=used,level=s['level'],reason=reason,result=result)
        s['history'].append(entry); save(s)
    return {**result,'hints_used':used,'level':s['level'],'reason':reason}

@app.get('/')
def home(): return FileResponse(ROOT/'frontend/index.html')

app.mount('/static',StaticFiles(directory=ROOT/'frontend'),name='static')
