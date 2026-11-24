# NORT DESKTOP AI — MVP 0.1

Aplicativo desktop Python para Windows com planejamento pela **Groq**, execução real de ferramentas e aprovação humana. O código não simula Excel, arquivos ou navegador. Esta entrega é código-fonte; o instalador Windows ainda precisa ser compilado e validado no Windows.

## Executar no Windows

1. Instale **Python 3.11 x64** e mantenha o **Microsoft Edge** instalado.
2. Extraia o projeto em uma pasta local e execute `Iniciar-Windows.cmd`. A primeira execução baixa as dependências pela internet.
3. Em **Configurações**, informe uma chave obtida em [Groq Console](https://console.groq.com/keys). A chave é salva no **Windows Credential Manager**, não em arquivo de configuração. Não envie a chave por chat.
4. O modelo inicial é `openai/gpt-oss-120b`, **hospedado na Groq**. Não usa a API OpenAI. Pode ser trocado em Configurações conforme o acesso da sua conta.
5. Escolha uma pasta com cópias dos arquivos de trabalho. Escreva o pedido, gere o plano, revise os argumentos e clique em **Aprovar e executar**.

Alternativa pelo PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m nort
```

A Groq disponibiliza plano gratuito com cotas, não uso ilimitado. O aplicativo informa erros de autenticação, indisponibilidade e limite HTTP 429; não contrata serviços nem troca automaticamente para provedores pagos. [Limites oficiais](https://console.groq.com/docs/rate-limits).

## Primeiro fluxo real

Coloque `admissoes.xlsx` na pasta escolhida, com cabeçalhos `nome`, `admissao` e `cpf`. Datas devem ser células de data do Excel ou texto ISO `YYYY-MM-DD`.

> Leia admissoes.xlsx, filtre admissao pelo mês 2026-09, valide nome e cpf e salve os registros em admissoes_setembro.xlsx. Confira o arquivo criado.

O arquivo de destino precisa ser novo. O MVP **não valida regras oficiais do eSocial**, CPF ou consistência fiscal: `validate_rows` verifica apenas presença dos campos. O envio para eSocial não está implementado.

É possível testar sem chave carregando `examples/plano-arquivos.json` em **Minhas automações**, escolhendo primeiro a pasta `examples`. Esse plano copia e verifica um arquivo real; não testa a IA.

## O que está implementado

- Interface PySide6 com campo de comando, plano JSON editável, logs visuais, tempo e captura de navegador quando solicitada no plano.
- Groq via HTTPS; resposta JSON validada contra ferramentas e assinaturas locais. Chave pelo cofre do sistema ou variável de ambiente `GROQ_API_KEY`.
- Modos assistido e automático. Ambos exigem aprovação inicial; o assistido confirma cada etapa. Vermelho confirma em ambos.
- Leitura, filtro, campos obrigatórios, criação XLSX e alteração de células em uma **cópia**. Fórmulas vindas dos dados são neutralizadas.
- Listagem, cópia, movimentação/renomeação e verificação SHA256. Sem sobrescrita e sem ferramenta de exclusão arbitrária.
- Playwright: URL HTTPS, leitura de texto, clique por role/nome, preenchimento por label, verificação de texto e captura PNG.
- Windows UI Automation: abertura de aplicativos permitidos, leitura de controles e clique por Automation ID/tipo. Depende da compatibilidade do aplicativo; Office deve estar instalado e seu executável localizável.
- Biblioteca local de planos, confirmações específicas e auditoria JSONL.
- Scripts PyInstaller + Inno Setup e workflow Windows para gerar `NORT-Desktop-AI-Setup.exe`.

## Limites claros desta versão

O plano é elaborado antes da execução, sem ciclo autônomo de replanejamento. Resultados intermediários podem alimentar ferramentas por `{"$ref":"id_da_etapa"}`; a IA não recebe planilhas, páginas ou capturas automaticamente. Se não conhece um seletor, solicita intervenção. Não há loops de cadastro em lote, OCR, gravação de processos, agendamento, PDF/Word, upload/download, integração fiscal ou recuperação automática. Essas funções são próximas etapas, não botões fictícios.

A pausa e o cancelamento valem **entre ferramentas**. Uma requisição Groq pode levar até 60 segundos; operações Playwright usam timeouts. Ações concluídas não são revertidas. Ao ocorrer erro, o executor para; não repete cliques ou envios. Rodar novamente um plano começa do início — revise resultados parciais antes.

O navegador é uma sessão isolada e fecha ao terminar/cancelar. Para login/MFA/CAPTCHA, inclua `human_checkpoint` e faça a intervenção manual antes de autorizar a continuação. Não há detecção universal de CAPTCHA. A lista de domínios bloqueia também recursos e redirecionamentos de outros hosts; autorize explicitamente os domínios de autenticação e recursos necessários. WebSockets e service workers estão desativados. A lista é um controle de aplicação, não um firewall de rede. Não é um navegador de uso geral.

## Segurança e dados

O modelo não define o risco. O catálogo marca leituras como verde, escrita local como amarelo e navegação/interação externa, abertura de aplicativo e movimentação como vermelho. A classificação conservadora evita depender da IA para identificar um botão fiscal ou financeiro. Revise **os argumentos concretos** no painel de confirmação; a descrição da IA pode estar errada.

Arquivos devem estar dentro da pasta escolhida. Não escolha o disco inteiro nem pastas de sistema. A política resolve caminhos e links simbólicos, mas não é uma sandbox de sistema operacional e não protege contra um processo local malicioso que troque links simultaneamente. Aplicativos abertos continuam sujeitos às permissões do usuário Windows. Não execute como administrador.

Comando e catálogo são enviados à Groq; não inclua senhas, CPF ou dados confidenciais no comando. Os resultados de ferramentas ficam locais. O preenchimento web envia o conteúdo ao site escolhido. A chave é armazenada no cofre do sistema. Planos, capturas, configuração e auditoria são locais e **não são criptografados pelo aplicativo**. Logs ocultam chaves em padrões conhecidos e argumentos de texto; não garantem anonimização de todo dado pessoal. Os arquivos de automação guardam argumentos para reutilização; não salve segredos neles.

No Windows: `%LOCALAPPDATA%\NortDesktopAI\config.json`, `automations\` e `logs\audit.jsonl`. Os logs registram usuário, horário UTC, comando, plano, decisões, etapas, arquivos, resultados resumidos e erros; não são imutáveis nem equivalem a auditoria regulatória.

## Gerar instalador Windows

Com Python 3.11, Edge e [Inno Setup 6](https://jrsoftware.org/isinfo.php) instalados:

```powershell
powershell -ExecutionPolicy Bypass -File installer\build.ps1
```

O script executa os testes antes do empacotamento. O resultado esperado é `dist\NORT-Desktop-AI-Setup.exe`, com assistente em português, atalho no menu Iniciar e atalho opcional na área de trabalho. Não embute chave API. A compilação precisa ocorrer no Windows; não há `.exe` previamente gerado nesta entrega. O workflow fornecido pode gerar um artefato quando colocado no seu repositório GitHub; nenhum repositório foi criado ou publicado.

O executável não terá assinatura digital até que o projeto obtenha certificado de assinatura. Antes de distribuir comercialmente, validar em Windows limpo, revisar licenças das dependências, assinar e testar desinstalação/atualização.

## Desenvolvimento e arquitetura

Veja [ARCHITECTURE.md](ARCHITECTURE.md), [VALIDATION.md](VALIDATION.md) e os testes em `tests/`.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Em macOS/Linux, o núcleo de arquivos/Excel e a interface podem ser testados, mas as ferramentas Windows retornam erro explícito. Para navegador fora do Windows, instale Chromium com `python -m playwright install chromium`.
