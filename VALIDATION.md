# Validação — 24/09/2026

Ambiente: macOS ARM64, Python 3.9.6, PySide6 6.10.3, openpyxl 3.1.5, Playwright 1.60.0, pytest 8.4.2. Alvo de distribuição: Windows com Python 3.11.

## Executado com sucesso

**38 testes passaram** na suíte padrão; 2 testes de navegador são opt-in e aparecem como ignorados nessa execução.

- Cópia real e verificação SHA256; destino existente preservado.
- Leitura de XLSX real, filtro mensal, validação de campos e criação de novo XLSX; referências entre etapas.
- Alteração de células em cópia mantendo o arquivo de origem.
- Neutralização de fórmulas no XLSX gerado.
- Rejeição de caminhos externos, links simbólicos para fora da pasta, streams alternativos e URLs/domínios não permitidos.
- Validação de planos, ferramentas desconhecidas, argumentos, IDs repetidos e referências futuras.
- Confirmação específica vermelha no modo automático, recusa, confirmação de leituras no assistido, falha interrompendo passos seguintes, pausa e cancelamento.
- Ocultação de padrões de chave e campos sensíveis em auditoria.
- Contrato HTTP Groq e erros 401/429/503 com respostas **simuladas nos testes**. Nenhuma chamada real Groq foi feita.
- Inicialização real da interface PySide6 em modo offscreen e execução real de cópia por QThread.
- Compilação sintática dos módulos e inspeção visual de `interface.png`.

Comando da suíte padrão: `python -m pytest -q`.

## Tentado, bloqueado pelo ambiente

Dois testes Playwright com Chromium real falharam na inicialização do navegador, antes de executar os cenários. A sandbox macOS retornou `bootstrap_check_in ... Permission denied (1100)`. Chromium e dependências foram baixados com sucesso; o bloqueio não é de rede. Não se considera navegação, clique, preenchimento ou captura de navegador verificados ponta a ponta nesta entrega.

Para executar em ambiente compatível:

```powershell
$env:NORT_BROWSER_TESTS = "1"
python -m pytest -q
```

Os testes de navegador usam HTML controlado, não sistemas externos. No Windows usam Edge instalado; em outros sistemas é necessário `python -m playwright install chromium`. O script de build habilita esses testes antes de empacotar.

## Pendente

- Chave real Groq: configurar localmente e gerar um plano com a conta do usuário.
- Cofre Windows Credential Manager e controle UI Automation em Windows.
- Navegação real, MFA/login manual e seleção de controles de um sistema autorizado.
- Build PyInstaller/Inno Setup em Windows limpo, instalação, atalhos, desinstalação e assinatura digital.

Não há instalador EXE compilado nesta entrega. O ZIP contém código, documentação, testes e scripts de build, não um binário Windows pronto.
