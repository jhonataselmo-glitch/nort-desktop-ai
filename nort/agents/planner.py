import json
import urllib.error
import urllib.request
from datetime import date
from nort.core.models import Plan


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class GroqPlanner:
    def __init__(self, key, model="openai/gpt-oss-120b"):
        self.key, self.model = key, model

    def create(self, command, registry):
        if not self.key: raise ValueError("Configure sua chave Groq em Configurações.")
        if not command.strip() or len(command) > 12000: raise ValueError("Comando vazio ou muito longo.")
        catalog = [t.describe() for t in registry.values()]
        prompt = """Você é o PLANNER do NORT Desktop AI. Responda exclusivamente JSON:
{"title":"Título", "steps":[{"id":"s1","description":"Ação concreta", "tool":"nome", "args":{}}]}.
Use APENAS as ferramentas do catálogo e os argumentos exatos das assinaturas.
Nunca gere código, comandos shell, senhas, seletores inventados ou dados fictícios.
Caminhos devem ser relativos à pasta escolhida. Referencie resultado de etapa anterior
com {"$ref":"s1"} como valor de argumento. Sem loops, sem interpolação, sem acesso por índice.
Para dados: read_excel retorna lista de objetos; filter_rows filtra; write_excel escreve lista.
Para seletores desconhecidos: browser_read e human_checkpoint; não adivinhe.
Se faltarem caminhos, campos ou informações essenciais, use human_checkpoint explicando o que falta.
Para CAPTCHA, MFA, senhas ou login: human_checkpoint para intervenção manual.
Não existe integração eSocial pronta: prepare dados e solicite revisão, sem alegar envio.
Inclua assert_file/assert_text quando pertinente. Nunca prometa uma ação sem ferramenta.
Máximo 40 etapas. A autorização é controlada pelo executor, não pelo plano.
"""
        payload = {"model": self.model, "temperature": 0.1,
                   "response_format": {"type": "json_object"},
                   "max_completion_tokens": 5000,
                   "messages": [{"role":"system", "content":prompt + "\nData: " + date.today().isoformat() + "\nCatálogo: " + json.dumps(catalog, ensure_ascii=False)},
                                {"role":"user", "content":command}]}
        req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(payload).encode(), headers={"Authorization":"Bearer " + self.key, "Content-Type":"application/json", "User-Agent":"NortDesktopAI/0.1"})
        try:
            with urllib.request.build_opener(NoRedirect).open(req, timeout=60) as response:
                body = json.load(response)
        except urllib.error.HTTPError as e:
            if e.code == 429: raise RuntimeError("Limite da Groq atingido. Aguarde e tente novamente; nenhum plano foi executado.") from None
            if e.code in (401,403): raise RuntimeError("Chave Groq inválida ou sem acesso ao modelo.") from None
            raise RuntimeError("Groq retornou HTTP %s. Confira modelo e disponibilidade." % e.code) from None
        except (urllib.error.URLError, TimeoutError):
            raise RuntimeError("Falha de conexão com a Groq. Nenhum plano foi executado.") from None
        choice = body["choices"][0]
        if choice.get("finish_reason") != "stop": raise ValueError("Resposta incompleta da IA. Gere o plano novamente.")
        return Plan.parse(choice["message"]["content"], registry)
