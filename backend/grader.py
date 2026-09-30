"""Local, trusted-code demo runner. A subprocess is NOT a security sandbox."""
from pathlib import Path
import os
import signal
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def run_tests(task_id, target, code, timeout=5):
    folder = ROOT / 'tasks' / task_id
    source = folder / ('reference.py' if target == 'reference' else f'variants/{target}.py')
    with tempfile.TemporaryDirectory(prefix='getgood-') as tmp:
        work = Path(tmp)
        (work/'svc.py').write_text(source.read_text())
        (work/'conftest.py').write_text((ROOT/'harness/conftest.py').read_text())
        (work/'test_submission.py').write_text(code)
        env = {k: os.environ[k] for k in ('PATH','SYSTEMROOT','WINDIR') if k in os.environ}
        env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        with (work/'output.txt').open('w+') as output:
            process = subprocess.Popen([sys.executable,'-m','pytest','-q','-p','no:cacheprovider',
                '--junitxml=result.xml','test_submission.py'], cwd=work, env=env,
                stdout=output, stderr=subprocess.STDOUT, start_new_session=os.name!='nt')
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name != 'nt': os.killpg(process.pid, signal.SIGKILL)
                else: process.kill()
                process.wait()
                return dict(status='timeout', tests=0, details=['Execution exceeded the time limit.'])
        if process.returncode not in (0,1) or not (work/'result.xml').exists():
            return dict(status='error', tests=0, details=['Tests could not be collected or executed. Check Python syntax and fixture usage.'])
        tree=ET.parse(work/'result.xml')
        cases=tree.findall('.//testcase')
        failures=[]
        errors=[]
        for case in cases:
            name=case.get('name','test')
            if case.find('error') is not None: errors.append(name)
            failure=case.find('failure')
            if failure is not None:
                # Only failed assertions are treated as behavioral evidence.
                message=failure.get('message','')
                if 'assert ' in message or 'AssertionError' in message: failures.append(name)
                else: errors.append(name)
        skipped=any(c.find('skipped') is not None for c in cases)
        if not cases or errors or skipped:
            return dict(status='error',tests=len(cases),details=errors or ['No complete executable test suite. Skips/xfails are not supported.'])
        return dict(status='failed' if failures else 'passed',tests=len(cases),details=failures)

def evaluate(task, submission):
    reference=run_tests(task['id'],'reference',submission['tests'])
    variants={}
    for variant in ['v1','v2','v3']:
        if reference['status']=='passed':
            result=run_tests(task['id'],variant,submission['tests'])
            variants[variant]={**result,'caught':result['status']=='failed'}
        else: variants[variant]=dict(status='not_run',caught=False,tests=0,details=[])
    expected=task['known_risks']
    claims=submission['judgements']
    def matches(risk, claim):
        lines=task.get('risk_locations',{}).get(risk['type'],[risk['line']])
        return claim['type']==risk['type'] and claim['line'] in lines
    hit=[risk for risk in expected if any(matches(risk,c) for c in claims)]
    missed=[risk for risk in expected if not any(matches(risk,c) for c in claims)]
    false_positive=[claim for claim in claims if not any(matches(r,claim) for r in expected)]
    judgement_ok=not missed and not false_positive
    consequence_ok=submission.get('consequence')==task['expected_consequence']
    boundaries={}
    for boundary in task['boundaries']:
        claim=submission['boundaries'].get(boundary['id'],'unverified')
        supported=bool(boundary['variants']) and all(variants[v]['caught'] for v in boundary['variants'])
        boundaries[boundary['id']]='supported' if claim=='verified' and supported else 'unsupported' if claim=='verified' else claim
    success=(judgement_ok and consequence_ok and reference['status']=='passed' and
             all(variants[v]['caught'] for v in task['required_variants']) and
             'unsupported' not in boundaries.values())
    return dict(judgement=dict(hit=hit,missed=missed,false_positive=false_positive,correct=judgement_ok),
        consequence=dict(correct=consequence_ok,selected=submission.get('consequence'),
                         expected=task['expected_consequence'] if consequence_ok else None),
        reference=reference,variants=variants,boundaries=boundaries,success=success)
