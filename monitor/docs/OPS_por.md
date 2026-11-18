<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OPS.md) | [🇪🇸 Español](OPS_spa.md) | [🇫🇷 Français](OPS_fra.md) | [🇮🇹 Italiano](OPS_ita.md) | [🇩🇪 Deutsch](OPS_deu.md) | [🇨🇳 简体中文](OPS_zho.md) | [🇯🇵 日本語](OPS_jpn.md) | **🇵🇹 Português**

# Operar a instalação

Para um monitor que fica a funcionar durante meses (edição Completa). Cobre a cópia de segurança completa, o restauro, a cópia agendada, o doctor com códigos de saída em que um cron pode confiar e como o montar como appliance (systemd ou Docker). A edição Lite não tem nada disto.

## O pacote de cópia

`python bin/monitor_cli.py backup create [FICHEIRO]` escreve UM `.zip` (formato 2) e verifica-o antes de o pôr no sítio. Sem `FICHEIRO` vai para a pasta `backups` da pasta de dados (`ops.backup.dir`) com o nome `ghamon-backup-<hora UTC>.zip`. Não é preciso parar o monitor: os dados são lidos com as leituras atómicas do armazenamento (ficheiros ou SQLite), nunca copiando uma base que está a ser escrita.

| Membro | O que contém |
|---|---|
| `dump.jsonl` | cada conta (as suas definições, o estado das sentinelas, os pequenos documentos, os eventos, as análises, os instantâneos da pontuação) e os registos globais (utilizadores e as contas que podem ver; nunca as sessões) |
| `files.json` | as definições da página e as listas da instalação (`targets.json`, `ecosystems.json`, `profiles.json`, os silêncios), limpas; também os armazenamentos dos módulos opcionais, se existirem (`proposals.json`, `devices.json`) |
| `manifest.json` | o formato, a versão do produto, o esquema, as contagens e o tamanho e o SHA-256 de cada membro |

**O que nunca viaja:** tokens e chaves do GitHub ou de uma App, palavras-passe, o valor de qualquer variável `*_env` (só o seu nome), o segredo do webhook, as chaves dos fornecedores de IA, as sessões e o conteúdo do armazém de segredos. As definições passam por uma lista branca (as mesmas chaves que a página de Definições pode mostrar) e depois por uma limpeza que descarta qualquer chave que pareça um segredo e qualquer texto que pareça um token ou uma chave privada. Com `ops.backup.include_config` desligado, as definições e as listas ficam totalmente de fora. Um restauro não traz de volta nenhuma credencial: volte a configurar o acesso ao GitHub (a lista de tarefas diz-o).

A cópia só pode ser lida pelo seu proprietário (modo 600) e o pacote não é cifrado a não ser que o peça: veja abaixo.

### Um pacote de uma só conta

`backup create --account ID [FICHEIRO]` escreve o pacote de UMA conta: o seu despejo (com as suas definições, limpas da mesma forma) e nada mais. Não leva nenhum utilizador nem sessão, nem as definições ou as listas da instalação; o manifesto diz `scope: account`. `backup verify` confere que contém só essa conta, e `backup restore FICHEIRO` restaura essa conta (não é preciso `--account`) sem tocar nas outras contas, nos utilizadores nem nos ficheiros do destino; só é recusado quando essa conta já existe lá e não há `--force`. É a forma de mover ou recuperar uma só conta.

### Cifrar a cópia (opcional)

`ops.backup.encrypt` (ou `--encrypt` para uma cópia) cifra o pacote com AES-256-GCM usando uma chave tirada da variável de ambiente que `ops.backup.key_env` indica (`--key-env NOME`). A chave nunca é uma definição, nunca é escrita e nunca vai numa linha de comandos. Precisa da biblioteca opcional `cryptography` (`pip install cryptography`; o núcleo do monitor continua a ser só biblioteca padrão). Sem a biblioteca, ou sem uma chave de 12 caracteres ou mais, a cópia é **recusada** com uma mensagem clara e não se escreve nada: nunca se faz uma cópia em claro quando pediu uma cifrada, nem se cifra com algo mais fraco. Um ficheiro cifrado termina em `.enc`; `verify` e `restore` abrem-no com a mesma variável. Guarde a chave separada do ficheiro: sem ela a cópia não se abre.

## Verificar, listar e estado

- `backup verify FICHEIRO` volta a ler o pacote e confere cada tamanho e SHA-256 e as contagens. Um byte alterado, um membro em falta ou um que o manifesto não lista é comunicado. `--deep` restaura-o também numa pasta temporária e confere o resultado.
- `backup list` mostra as cópias da pasta; `backup status` mostra a última cópia boa, a sua idade, o agendamento e a última falha.
- Um pacote do primeiro formato (feito antes da 2.1.0) continua a verificar-se e a restaurar-se.

## Restaurar

`python bin/monitor_cli.py backup restore FICHEIRO`: pare primeiro o monitor (o restauro é recusado enquanto um responder na sua porta). Verifica o pacote e depois escreve as contas e os ficheiros.

- Um armazenamento que já tem contas é recusado, a não ser que junte `--force` (as contas do pacote são então escritas por cima; as definições são **fundidas**: uma chave que o pacote não leva nunca é removida).
- `--account ID` restaura só essa conta e deixa as outras e os ficheiros globais como estão (recusado apenas quando essa conta existe e não há `--force`).
- `--to-dir PASTA` restaura numa pasta vazia (backend de ficheiros) sem tocar na instalação: a forma de ver uma cópia ou de mudar para outra máquina.
- Escreve `ops/restore_report.json` na pasta de dados e imprime o que falta fazer: voltar a configurar o acesso ao GitHub, voltar a definir as definições que o pacote deixou de fora, reiniciar o monitor para que o supervisor arranque cada conta, executar o doctor.

## A cópia agendada

Duas formas, use uma:

1. Dentro do monitor: `ops.backup.enabled` (desligado por predefinição) faz uma cópia a cada `ops.backup.interval_hours` num fio próprio, mantém as `ops.backup.keep` mais recentes (só se removem ficheiros com nome de cópia) e regista o resultado em `ops/backup_status.json`. Uma falha (disco cheio, chave em falta) fica registada e é mostrada no painel Acerca de e no doctor; nunca para o monitor.
2. Com systemd: `deploy/github-actions-monitor-backup.service` e `deploy/github-actions-monitor-backup.timer` (veja abaixo).

O painel Acerca de tem um cartão **Operação** com o modo (serviço ou local), a última cópia boa, o agendamento, a retenção em vigor e o botão **Copiar agora** (um administrador, a partir deste computador). `GET /api/ops/status` dá os mesmos dados; `POST /api/ops/backup` faz uma cópia.

## Purga a pedido

A purga de retenção corre sozinha a cada `retention.interval_hours`. Para a executar já há um botão (e `POST /api/ops/purge`) que **não existe** enquanto `ops.purge.enabled` não estiver ligado (desligado por predefinição). Um pedido é um ensaio (a política em vigor e quantos eventos sairiam), a não ser que diga `dry_run` false, e uma purga real é recusada sem uma cópia boa mais recente do que `ops.purge.require_backup_hours` (24 por predefinição; 0 não o exige). Deixa a sua linha na auditoria da retenção e no registo de ações.

## O doctor e os seus códigos de saída

`python bin/monitor_cli.py doctor [--strict] [--json]` (ou `python bin/actions_monitor.py --doctor`) verifica a instalação, não altera nada e não imprime nenhum segredo. A edição Completa acrescenta estas verificações depois das habituais:

| Verificação | O que observa |
|---|---|
| `volumes` | um ficheiro é mesmo escrito, lido e removido nas pastas de dados, registos e cópias (um volume Docker montado como root ou só de leitura falha aqui) |
| `supervisor` | um monitor em execução: a saúde profunda do supervisor e de cada ciclo de atualização (não se arranca nada) |
| `limits` | o segredo do webhook está definido e tem pelo menos `ops.doctor.webhook_min_length` caracteres (só se compara o comprimento) e a política de retenção |
| `sqlite_hot` | cada base SQLite aberta só para leitura: `quick_check` (predefinição) ou `integrity_check` (`ops.doctor.sqlite_check` deep), cortada em `ops.doctor.sqlite_timeout_s`; um ficheiro corrompido após um corte de energia falha |
| `backup_age` | a última cópia boa face a `ops.doctor.backup_max_age_days` |
| `disk` | espaço livre do volume de dados face a `ops.doctor.min_free_mb` |
| `metrics` | `/metrics` responde quando a saída Prometheus está ligada e há um monitor em execução |

**Códigos de saída (estáveis, para cron):** `0` tudo bem (também com avisos, sem `--strict`); `1` falhou pelo menos uma verificação; `3` só avisos e `--strict` (ou `ops.doctor.strict_exit`); `4` o próprio doctor não conseguiu executar-se. São os códigos do doctor; os outros comandos de `monitor_cli.py` mantêm os seus. Exemplo: `0 * * * * python3 bin/monitor_cli.py doctor --strict --json > /var/lib/github-actions-monitor/doctor.json || true` e alerte para qualquer código diferente de 0.

## Como appliance

**systemd** (sem contentor): siga os comentários de `deploy/github-actions-monitor.service` e instale depois a unidade de cópia e o seu temporizador:

```
install -m 644 deploy/github-actions-monitor-backup.service deploy/github-actions-monitor-backup.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor-backup.timer
systemctl list-timers github-actions-monitor-backup.timer
```

Para uma cópia cifrada ponha a variável que `ops.backup.key_env` indica em `/etc/github-actions-monitor/env` (modo 600). O temporizador executa `backup create` todos os dias; o seu código de saída é 1 quando a cópia não pôde ser feita.

**Docker:** `deploy/compose.yaml` guarda as cópias num volume próprio (`monitor-backups` em `/data/backups`) para que perder o volume de dados não as perca. Tire um ficheiro com `docker compose exec monitor python bin/monitor_cli.py backup list` e `docker cp`, e restaure num contentor parado ou com `--to-dir`. O TLS é renovado pelo Caddy de `deploy/Caddyfile`.

**Atualizar sem perder as contas:** `backup create` → `backup verify FICHEIRO` → parar o monitor → substituir a pasta do produto (as pastas `config/`, `data/`, `logs/` e `ai/` são suas e mantêm-se) → `doctor` → arrancar. Se algo correr mal, `backup restore FICHEIRO`. **Removê-lo de forma limpa:** pare e desative as unidades, remova o temporizador, depois a pasta do produto e, só se quiser perder os dados, as pastas `config/`, `data/` ou os volumes Docker.

## Definições

Estão todas no separador Definições (Pastas e ficheiros) e em [SETTINGS_por.md](SETTINGS_por.md): `ops.backup.*` (enabled, dir, interval_hours, keep, include_config, compress_level, encrypt, key_env), `ops.purge.*` (enabled, require_backup_hours) e `ops.doctor.*` (strict_exit, backup_max_age_days, min_free_mb, sqlite_check, sqlite_timeout_s, webhook_min_length). Cada interruptor começa desligado ou conservador, e os de segurança (a cópia agendada, incluir as definições, a cifragem, a purga) estão marcados como tal.

Veja também [STORAGE_por.md](STORAGE_por.md) (os backends e a retenção), [DEPLOYMENT_por.md](DEPLOYMENT_por.md) (serviço, contentor, TLS) e [CLI_por.md](CLI_por.md).
