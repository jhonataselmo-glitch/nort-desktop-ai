import json
import threading
from pathlib import Path
import pytest
from nort.core.models import Plan, Step
from nort.core.executor import Executor
from nort.tools.registry import registry, Tool
from nort.security.policy import Policy
from nort.security.audit import Audit, redact


@pytest.fixture
def context(tmp_path):
    tools, _ = registry(Policy(tmp_path, ['example.com']))
    return tmp_path, tools, Audit(tmp_path/'audit.jsonl')


def plan(*steps):
    return Plan('Teste', [Step(str('s'+str(i)),desc,tool,args) for i,(desc,tool,args) in enumerate(steps)])


@pytest.mark.parametrize('path',['../outside.txt','../../escape','//server/share','file.txt:stream','C:relative'])
def test_reject_path_escape(tmp_path,path):
    with pytest.raises(PermissionError): Policy(tmp_path).path(path)


def test_reject_symlink_escape(tmp_path):
    outside=tmp_path.parent/'external';outside.mkdir(exist_ok=True)
    link=tmp_path/'link'
    try: link.symlink_to(outside,target_is_directory=True)
    except OSError: pytest.skip('Symlink permission not available')
    with pytest.raises(PermissionError): Policy(tmp_path).path('link/private.txt')


@pytest.mark.parametrize('url',['http://example.com','https://example.com.evil.test','https://other.test','https://user:pass@example.com','file:///tmp/a','https://example.com:8443'])
def test_domain_boundary(tmp_path,url):
    with pytest.raises(PermissionError):Policy(tmp_path,['example.com']).url(url)


def test_valid_domain(tmp_path):
    assert Policy(tmp_path,['example.com']).url('https://example.com/path')


@pytest.mark.parametrize('mutation',[
    lambda p:p['steps'][0].update(tool='shell'),
    lambda p:p['steps'][0].update(risk='verde'),
    lambda p:p['steps'][0].update(args={'command':'rm'}),
    lambda p:p['steps'][0].update(args={'subfolder':{'$ref':'later'}}),
    lambda p:p.update(steps=[]),
    lambda p:p['steps'].append(p['steps'][0].copy()),
])
def test_invalid_plans_rejected(context,mutation):
    _,tools,_=context
    obj=json.loads(plan(('Listar','list_files',{})).to_json());mutation(obj)
    with pytest.raises((ValueError,TypeError)):Plan.parse(json.dumps(obj),tools)


def test_red_requires_specific_approval_in_automatic(context):
    root,tools,audit=context
    (root/'source.txt').write_text('abc')
    decisions=[]
    def reject(step,tool,args):decisions.append((tool.name,args));return False
    engine=Executor(tools,audit,reject)
    engine.run(plan(('Mover','move_file',{'source':'source.txt','destination':'dest.txt'})),'automatico')
    assert (root/'source.txt').exists() and not (root/'dest.txt').exists()
    assert decisions==[('move_file',{'source':'source.txt','destination':'dest.txt'})]
    assert 'run_cancelled' in (root/'audit.jsonl').read_text()


def test_assisted_approves_reads(context):
    _,tools,audit=context
    calls=[]
    Executor(tools,audit,lambda *args:calls.append(args) or True).run(plan(('Listar','list_files',{})))
    assert len(calls)==1


def test_automatic_green_needs_no_step_approval(context):
    _,tools,audit=context
    def fail(*args):raise AssertionError('Unexpected approval')
    Executor(tools,audit,fail).run(plan(('Listar','list_files',{})),'automatico')


def test_copy_real_and_no_overwrite(context):
    root,tools,audit=context
    (root/'a.txt').write_text('real data')
    p=plan(('Copiar','copy_file',{'source':'a.txt','destination':'b.txt'}),('Verificar','assert_file',{'path':'b.txt'}))
    result=Executor(tools,audit,lambda *a:True).run(p,'automatico')
    assert (root/'b.txt').read_text()=='real data'
    assert result['s0']['sha256']==result['s1']['sha256']
    with pytest.raises(FileExistsError):Executor(tools,audit,lambda *a:True).run(p,'automatico')
    assert (root/'b.txt').read_text()=='real data'


def test_failure_stops_later_actions(context):
    root,tools,audit=context
    (root/'a.txt').write_text('keep')
    p=plan(('Falhar','assert_file',{'path':'missing'}),('Copiar','copy_file',{'source':'a.txt','destination':'b.txt'}))
    with pytest.raises(ValueError):Executor(tools,audit,lambda *a:True).run(p,'automatico')
    assert not (root/'b.txt').exists()
    assert 'run_failed' in (root/'audit.jsonl').read_text()


def test_cancel_before_execution(context):
    _,tools,audit=context
    engine=Executor(tools,audit,lambda *a:True);engine.cancel()
    assert engine.run(plan(('Listar','list_files',{})))=={}


def test_pause_cancel_unblocks(context):
    _,tools,audit=context
    engine=Executor(tools,audit,lambda *a:True);engine.pause()
    done=threading.Event()
    t=threading.Thread(target=lambda:(engine.run(plan(('Listar','list_files',{}))),done.set()))
    t.start();assert not done.wait(.05);engine.cancel();t.join(2)
    assert done.is_set()


def test_audit_redacts_keys_and_text():
    result=redact({'password':'secret','text':'private','message':'key gsk_abcdef12345'})
    assert 'secret' not in str(result) and 'private' not in str(result) and 'abcdef' not in str(result)


def test_references_excel_real(context):
    from openpyxl import Workbook, load_workbook
    from datetime import datetime
    root,tools,audit=context
    wb=Workbook();ws=wb.active;ws.append(['nome','admissao'])
    ws.append(['Ana',datetime(2026,9,3)]);ws.append(['Bia',datetime(2026,8,1)])
    wb.save(root/'input.xlsx');wb.close()
    p=plan(('Ler','read_excel',{'path':'input.xlsx'}),
           ('Filtrar','filter_rows',{'rows':{'$ref':'s0'},'column':'admissao','operator':'month','value':'2026-09'}),
           ('Validar','validate_rows',{'rows':{'$ref':'s1'},'required_columns':['nome','admissao']}),
           ('Gravar','write_excel',{'path':'output.xlsx','rows':{'$ref':'s2'}}),
           ('Verificar','assert_file',{'path':'output.xlsx'}))
    result=Executor(tools,audit,lambda *a:True).run(p,'automatico')
    assert result['s3']['rows']==1
    out=load_workbook(root/'output.xlsx');assert out.active['A2'].value=='Ana';assert out.active.max_row==2;out.close()


def test_excel_prevents_formula_injection_and_overwrite(context):
    from openpyxl import load_workbook
    root,tools,_=context
    write=tools['write_excel'].handler
    write('out.xlsx',[{'nome':'=HYPERLINK("bad")'}])
    wb=load_workbook(root/'out.xlsx');assert wb.active['A2'].data_type=='s';wb.close()
    with pytest.raises(ValueError):write('out.xlsx',[{'nome':'new'}])


def test_update_excel_preserves_source(context):
    from openpyxl import load_workbook
    root,tools,_=context
    tools['write_excel'].handler('source.xlsx',[{'nome':'Ana'}])
    tools['update_excel'].handler('source.xlsx','copy.xlsx',{'A2':'Bia'})
    a=load_workbook(root/'source.xlsx');b=load_workbook(root/'copy.xlsx')
    assert a.active['A2'].value=='Ana' and b.active['A2'].value=='Bia';a.close();b.close()


def test_required_columns_missing(context):
    _,tools,_=context
    with pytest.raises(ValueError):tools['validate_rows'].handler([{'nome':''}],['nome'])


def test_atomic_plan_snapshot_and_resolved_approval(context):
    _,tools,audit=context
    seen=[]
    tools['source']=Tool('source','verde',lambda:[{'nome':'Ana'}],'TEST')
    tools['sink']=Tool('sink','vermelho',lambda rows:len(rows),'TEST')
    p=plan(('Ler','source',{}),('Enviar','sink',{'rows':{'$ref':'s0'}}))
    def approve(step,tool,args):
        seen.append(args);p.steps.clear();return True
    result=Executor(tools,audit,approve).run(p,'automatico')
    assert result['s1']==1 and seen==[{'rows':[{'nome':'Ana'}]}]
