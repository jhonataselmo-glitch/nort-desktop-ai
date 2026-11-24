# Arquitetura do MVP

## Decisões

Python 3.11 no Windows é o alvo de distribuição. PySide6 mantém a interface nativa responsiva com execução em QThread. Playwright usa seletores acessíveis e verificações; pywinauto usa Microsoft UI Automation. openpyxl manipula XLSX sem exigir Excel instalado. O planner chama diretamente a API Groq, sem dependência de SDK OpenAI. `keyring` usa backend explícito WinVault, sem fallback para arquivo de senha. PyInstaller e Inno Setup fazem o empacotamento no Windows.

## Pastas

```text
nort/
  __main__.py          entrada desktop
  ui/main.py           interface, biblioteca e comunicação com worker
  core/models.py       plano e validação de ferramentas/argumentos/referências
  core/executor.py     estado, confirmações, execução e cancelamento
  agents/planner.py    integração Groq e planejamento estruturado
  tools/registry.py    catálogo e roteamento por agente
  tools/data.py        Excel e transformação de registros
  tools/files.py       cópia, movimentação e validação
  tools/browser.py     sessão Playwright isolada
  tools/windows.py     UI Automation
  security/policy.py   limites de pasta e domínios
  security/credentials.py  cofre de credenciais
  security/audit.py    auditoria local
examples/              plano local executável sem IA
tests/                 testes do núcleo e integrações locais
installer/             build Windows e assistente Inno Setup
.github/workflows/     validação e empacotamento Windows
```

PLANNER, DATA AGENT, BROWSER AGENT e WINDOWS AGENT são responsabilidades modulares; não são múltiplos LLMs consumindo cotas. SECURITY GUARD é código determinístico e VALIDATOR corresponde às verificações locais e ferramentas `assert_*`. DOCUMENT AGENT é uma extensão futura.

## Execução de uma tarefa

1. Usuário seleciona pasta, domínios e modo. O pedido é enviado à Groq com data local e catálogo; arquivos não são enviados.
2. Groq devolve um JSON. O parser rejeita ferramentas desconhecidas, campos inesperados, argumentos incompatíveis, IDs repetidos, referências futuras e mais de 40 passos.
3. Usuário revisa ou edita o JSON. A aprovação inicial é exigida pela interface; o executor revalida e tira uma cópia do plano ao iniciar.
4. Executor resolve referências de resultados anteriores. O risco é buscado no catálogo local, nunca em texto produzido pelo modelo.
5. Cada passo assistido ou vermelho recebe autorização específica dos argumentos já resolvidos. Recusar cancela os passos seguintes.
6. Ferramenta executa dentro de suas restrições. Resultados e verificações aparecem no painel; audit registra metadados, sem enviar observações ao modelo.
7. Falha interrompe. Retomada automática não existe; o operador revisa e prepara outro plano, evitando repetição inadvertida.

O registro `human_checkpoint` confirma somente que o operador reconheceu a mensagem; não prova que uma ação manual foi realizada. Tarefas críticas precisam de uma verificação explícita depois.

## Extensão

Nova ferramenta deve ter argumentos delimitados, implementação testável, risco determinado no catálogo e verificação de resultado. Nunca adicionar `eval`, shell arbitrário ou execução de código gerado. Futuro replanejamento deve tratar páginas e documentos como dados não confiáveis e exigir nova autorização para mudança de efeito/destino. Agendamentos devem persistir consentimento delimitado e permanecer bloqueados em ações vermelhas até confirmação humana.

## Referências consultadas

- https://console.groq.com/docs/openai
- https://console.groq.com/docs/structured-outputs
- https://console.groq.com/docs/rate-limits
- https://doc.qt.io/qtforpython-6/
- https://playwright.dev/python/docs/intro
- https://playwright.dev/python/docs/browsers
- https://pywinauto.readthedocs.io/en/latest/getting_started.html
