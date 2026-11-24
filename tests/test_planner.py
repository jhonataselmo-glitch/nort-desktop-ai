import io
import json
import urllib.error
import pytest
from nort.agents.planner import GroqPlanner
from nort.security.policy import Policy
from nort.tools.registry import registry


def test_groq_request_and_parse(monkeypatch,tmp_path):
    tools,_=registry(Policy(tmp_path))
    content=json.dumps({'title':'Listar','steps':[{'id':'s1','description':'Listar','tool':'list_files','args':{}}]})
    class FakeOpener:
        def open(self,req,timeout):
            assert req.full_url=='https://api.groq.com/openai/v1/chat/completions'
            body=json.loads(req.data)
            assert body['model']=='openai/gpt-oss-120b'
            assert body['response_format']=={'type':'json_object'}
            assert timeout==60
            return io.BytesIO(json.dumps({'choices':[{'finish_reason':'stop','message':{'content':content}}]}).encode())
    monkeypatch.setattr('urllib.request.build_opener',lambda *a:FakeOpener())
    assert GroqPlanner('test-key').create('Liste arquivos',tools).steps[0].tool=='list_files'


@pytest.mark.parametrize('code,message',[(429,'Limite'),(401,'Chave'),(503,'HTTP')])
def test_api_errors_safe(monkeypatch,tmp_path,code,message):
    tools,_=registry(Policy(tmp_path))
    class FakeOpener:
        def open(self,*a,**k):raise urllib.error.HTTPError('url',code,'secret-provider-body',{},None)
    monkeypatch.setattr('urllib.request.build_opener',lambda *a:FakeOpener())
    with pytest.raises(RuntimeError,match=message) as err:GroqPlanner('test-key').create('Listar',tools)
    assert 'secret-provider-body' not in str(err.value)


def test_missing_key(tmp_path):
    tools,_=registry(Policy(tmp_path))
    with pytest.raises(ValueError,match='chave'):GroqPlanner('').create('Listar',tools)
