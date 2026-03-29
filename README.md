# mailmap

Inventário de serviços vinculados a um e-mail via análise de caixa postal por IMAP.

O projeto escaneia a mailbox inteira, reaproveita cache local em SQLite, cruza headers, remetentes, links, HTML, texto e recorrência, e produz um inventário conservador de serviços provavelmente ligados ao endereço analisado.

Além do inventário, o `mailmap` também pode:

- gerar um plano de higiene da inbox;
- montar ações de unsubscribe quando existirem mecanismos padrão;
- arquivar tráfego de baixa prioridade por serviço.

> [!IMPORTANT]
> O fluxo principal continua sendo simples: copiar `.env.example`, preencher as credenciais e rodar `mailmap`.

> [!NOTE]
> O projeto prioriza precisão e explicabilidade. Quando a evidência não sustenta certeza, o `mailmap` rebaixa o resultado para `likely-account`, `weak-signal`, `newsletter-only` ou `ambiguous`.

## Instalação rápida

Entre no diretório do projeto, crie a venv e instale:

```bash
cd /home/ven/Projects/mailmap
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Para desenvolvimento e testes:

```bash
pip install -e .[dev]
```

No `fish`:

```fish
source .venv/bin/activate.fish
```

## Fluxo normal

Uso esperado:

1. copiar `.env.example` para `.env`;
2. preencher host IMAP, e-mail e senha;
3. rodar `mailmap`.

Fluxo mínimo:

```bash
cp .env.example .env
mailmap
```

O comando padrão faz:

1. leitura de `.env` e variáveis de ambiente;
2. conexão segura por IMAP SSL;
3. descoberta de pastas úteis;
4. scan completo com UIDs em lotes;
5. reaproveitamento incremental do cache SQLite;
6. atribuição de serviços com score explicável;
7. geração automática de relatórios.

Arquivos gerados no fluxo normal:

- `services.json`
- `services.csv`
- `report.md`
- `mailmap_cache.sqlite3`

Arquivos gerados quando ações extras são pedidas:

- `hygiene.json`
- `hygiene.md`
- `unsubscribe_actions.json`
- `unsubscribe_actions.md`
- `clean_results.json`
- `clean_results.csv`

## O que o projeto faz

Durante uma execução normal, o `mailmap`:

1. carrega configuração de CLI, ambiente e `.env`;
2. valida a configuração e avisa cedo quando o provedor for problemático;
3. abre a sessão IMAP em modo seguro;
4. escolhe automaticamente pastas úteis como `INBOX`, `All Mail`, `Archive` e `Sent`;
5. ignora pastas claramente inúteis, como spam e lixeira, por padrão;
6. busca mensagens por UID em lotes e salva payload parseado em SQLite;
7. extrai sinais de headers, assunto, corpo texto, HTML e links;
8. normaliza domínios, reduz ruído de infraestrutura e rastreamento;
9. consolida evidência por serviço com score conservador;
10. exporta resultados legíveis para uso manual e pós-processamento.

Quando flags de ação são usadas, o projeto também pode:

11. gerar recomendações de higiene por serviço;
12. montar ou executar unsubscribe via `List-Unsubscribe`;
13. arquivar tráfego de baixa prioridade via IMAP.

## Alvo do projeto

O projeto foi desenhado para o seguinte cenário:

- análise de caixa postal pessoal;
- provedores IMAP tradicionais;
- reruns incrementais com cache local;
- uso local em Linux com Python 3.12+.

Provedores mais simples:

- Gmail
- Fastmail
- Proton Bridge
- outros provedores IMAP tradicionais com senha de app ou IMAP clássico

Provedores problemáticos:

- Outlook / Hotmail

> [!WARNING]
> Contas Microsoft pessoais são suporte experimental. Muitas bloqueiam IMAP clássico e podem exigir app registration próprio em Azure ou Microsoft Entra para OAuth.

> [!NOTE]
> O projeto não promete “plug-and-play” universal para todos os provedores. A prioridade é ter um fluxo confiável onde IMAP realmente é viável.

## Configuração

Crie o arquivo local:

```bash
cp .env.example .env
```

Variáveis principais:

- `MAILMAP_IMAP_HOST`
- `MAILMAP_IMAP_PORT`
- `MAILMAP_EMAIL`
- `MAILMAP_PASSWORD`
- `MAILMAP_OUTPUT_DIR`

Variáveis opcionais:

- `MAILMAP_DEFAULT_FOLDERS`
- `MAILMAP_AUTH_MODE`
- `MAILMAP_MICROSOFT_CLIENT_ID`
- `MAILMAP_MICROSOFT_TENANT`
- `MAILMAP_SMTP_HOST`
- `MAILMAP_SMTP_PORT`

Exemplo simples para Gmail:

```env
MAILMAP_IMAP_HOST=imap.gmail.com
MAILMAP_IMAP_PORT=993
MAILMAP_EMAIL=voce@gmail.com
MAILMAP_PASSWORD=sua_senha_de_app
MAILMAP_AUTH_MODE=basic
MAILMAP_OUTPUT_DIR=results
```

Exemplo para Outlook/Hotmail com OAuth:

```env
MAILMAP_IMAP_HOST=imap-mail.outlook.com
MAILMAP_IMAP_PORT=993
MAILMAP_EMAIL=voce@hotmail.com
MAILMAP_AUTH_MODE=microsoft-oauth
MAILMAP_MICROSOFT_CLIENT_ID=seu-client-id-real
MAILMAP_MICROSOFT_TENANT=consumers
MAILMAP_OUTPUT_DIR=results
```

> [!TIP]
> Para Gmail, o caminho normal é usar senha de app, não a senha principal da conta.

## Interação esperada

Na maior parte do tempo, o projeto roda sem prompts extras.

Ainda assim, algumas situações podem exigir interação:

- autenticação inicial OAuth da Microsoft;
- login por browser em device-code flow;
- unsubscribe manual via link HTTP quando não houver `mailto:`;
- revisão humana antes de usar `-c` em serviços específicos.

> [!IMPORTANT]
> `-y` não altera a caixa postal. Ele apenas gera um plano de ação.

> [!WARNING]
> `-c` modifica a mailbox. Ele move mensagens para a pasta de arquivo quando encontra um destino apropriado.

## Opções disponíveis

Comando base:

```bash
mailmap
```

Flags:

- `--since YYYY-MM-DD`
  Escaneia apenas mensagens a partir da data informada.
- `--quick`
  Usa uma análise mais leve e rápida, útil para primeira validação do pipeline.
- `--output DIR`
  Grava os artefatos em outro diretório.
- `-c`, `--clean`
  Arquiva tráfego de baixa prioridade por serviço.
- `-u`, `--unsub`
  Gera ações de unsubscribe e, quando possível, executa unsubscribe por `mailto:`.
- `-y`, `--hygiene`
  Gera um plano de higiene da inbox.
- `-s`, `--services "A,B,C"`
  Restringe `clean` e `unsub` aos serviços informados.
- `-h`, `--help`
  Mostra a ajuda.

Exemplos:

```bash
mailmap
mailmap --since 2024-01-01
mailmap --quick
mailmap --output results/
mailmap -y
mailmap -u
mailmap -c
mailmap -c -u -s "Pinterest,Spotify,Twitch"
```

## O que `-y`, `-u` e `-c` fazem

### `-y`, `--hygiene`

Não altera nada na inbox.

Ele só gera recomendações por serviço, por exemplo:

- `keep`
- `keep-but-mute`
- `unsubscribe-and-archive`
- `archive-or-delete`

Arquivos:

- `hygiene.json`
- `hygiene.md`

### `-u`, `--unsub`

Tenta encontrar mecanismos de unsubscribe em `List-Unsubscribe`.

Comportamento:

- se houver `mailto:`, pode enviar unsubscribe por SMTP quando configurado;
- se houver link HTTP, gera o plano para ação manual;
- evita prometer unsubscribe universal para qualquer serviço.

Arquivos:

- `unsubscribe_actions.json`
- `unsubscribe_actions.md`

### `-c`, `--clean`

Modifica a mailbox.

Comportamento:

1. escolhe os serviços-alvo;
2. localiza mensagens mapeadas para esses serviços;
3. procura uma pasta de arquivo (`All Mail` ou `Archive`);
4. copia para o destino;
5. remove da pasta de origem.

Arquivos:

- `clean_results.json`
- `clean_results.csv`

> [!TIP]
> Sem `-s`, `clean` e `unsub` atuam primeiro em serviços `newsletter-only` e `weak-signal`.

## Saídas principais

### `services.json`

Inventário completo em formato estruturado, com:

- nome canônico;
- domínios associados;
- confiança;
- status;
- categorias;
- contagem de emails;
- datas;
- resumo de evidência;
- remetentes representativos;
- assuntos representativos;
- ação recomendada.

### `services.csv`

Exportação plana para planilha.

### `report.md`

Relatório humano legível com:

- serviço;
- score;
- status;
- categorias;
- datas;
- resumo;
- razões do score;
- ação recomendada.

### `mailmap_cache.sqlite3`

Cache local e checkpoint incremental.

## Estrutura do projeto

```text
src/mailmap/
  actions.py
  aggregation.py
  app.py
  cli.py
  config.py
  content.py
  database.py
  domains.py
  evidence.py
  exporters.py
  fingerprints.py
  imap_client.py
  message_parser.py
  models.py
  oauth.py
  scoring.py
  ui.py
tests/
examples/
```

## Precisão e limites

O projeto já faz:

- redução de falsos positivos por domínio;
- distinção entre infra, tracking e marca real;
- rebaixamento de streams dominados por newsletter;
- penalidade por proporção fraca entre evidência forte e volume total;
- fallback para `ambiguous` quando a atribuição não estiver limpa.

Limites reais:

- unsubscribe não é universal;
- desvinculação de conta não faz parte do fluxo automático;
- alguns provedores quebram a simplicidade do setup por decisão deles, não do projeto;
- atribuição perfeita para qualquer inbox do mundo não é uma meta realista.

> [!NOTE]
> O objetivo do `mailmap` é produzir um inventário defensável e útil, não fingir certeza onde a evidência é incompleta.

## Verificação local

Rodar testes:

```bash
PYTHONPATH=src .venv/bin/pytest -q
```

Ver ajuda da CLI:

```bash
PYTHONPATH=src .venv/bin/mailmap --help
```

## Arquivos de exemplo

Veja:

- [examples/services.json](examples/services.json)
- [examples/services.csv](examples/services.csv)
- [examples/report.md](examples/report.md)
