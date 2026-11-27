<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLIANCE.md) | [🇪🇸 Español](COMPLIANCE_spa.md) | [🇫🇷 Français](COMPLIANCE_fra.md) | [🇮🇹 Italiano](COMPLIANCE_ita.md) | [🇩🇪 Deutsch](COMPLIANCE_deu.md) | [🇨🇳 简体中文](COMPLIANCE_zho.md) | [🇯🇵 日本語](COMPLIANCE_jpn.md) | **🇵🇹 Português**

# Conformidade: o que pode demonstrar sobre a sua instalação

Tudo aqui está desligado de fábrica e só funciona na edição completa, exceto as duas restrições, que valem para qualquer processo do monitor. Nada disto é uma certificação.

## Modo estrito só de leitura

`security.read_only_strict` (desligado). Ligado, nada é escrito no GitHub digam o que disserem a edição ou as outras definições: só arrancam comandos de leitura do `gh` (o que não se sabe que lê é recusado), sem `git push`, sem `act` e sem pedidos à API do GitHub além de GET ou HEAD. É imposto por baixo de todas as partes, com um gancho de auditoria do Python que vê cada programa arrancado. Só se altera no computador do monitor e aliviar exige reiniciar. A janela Acerca de e `/api/about` (`restrictions`) dizem se está em vigor.

## Política de rede

`security.egress_policy`: `default`, `github_only` ou `none`; `security.egress_allow` acrescenta anfitriões (`nome`, `*.nome`, um endereço) ou `program:NOME`. Com `github_only` os processos do monitor só chegam a `api.github.com`, `uploads.github.com`, ao anfitrião de `GH_HOST` (GitHub Enterprise) e ao que permitir; com `none`, só a este computador, e o `gh` não é arrancado. Os programas que abrem a rede por si (`git` em comandos de rede, `apprise`, `curl`, `docker`, as ferramentas dos cofres de segredos) não são arrancados. Uma ligação recusada falha com um erro que indica a definição. `python bin/monitor_cli.py doctor` falha quando um destino configurado está fora da política, e `doctor --egress` lista todos os destinos. Não é uma firewall: não governa o que os outros programas do computador fazem.

## O relatório de conformidade

`python bin/monitor_cli.py compliance report` (com `--json`), `GET /api/compliance/report` (administradores) e uma caixa no fim do separador Segurança. Cada linha diz se foi **verificada** (o monitor olhou) ou só **declarada** (a configuração diz): versão e suporte, edição, autenticação e fornecedor de identidade, modo de rede e TLS, as duas restrições e os destinos, retenção e retenção legal, registo de ações e a sua cadeia, cópias e cifragem, cifragem em repouso (nenhuma), armazenamento, extensões, implantação e perfil. Sem segredos, caminhos ou nomes. `GET /api/compliance/state` dá as restrições, a tabela de retenção e o estado da exportação.

## Retenção e retenção legal

Eventos, análises e pontuações mantêm as suas definições (`retention.events_days`, `retention.analytics_days`, `retention.mode`). As outras categorias ficam para sempre salvo se lhes der dias: `retention.audit_days` (ficheiros rodados inteiros do registo de ações), `retention.reports_days` (fica o relatório mais recente de cada conta), `retention.ai_log_days`, `retention.backups_days` (fica a cópia mais recente). Cada eliminação deixa uma linha no registo de ações. `retention.legal_hold` para toda a remoção: eventos, análises, pontuações, relatórios, cópias, o corte do feed e do registo de prompts, e a rotação e limpeza do registo. As propostas da IA caducam sozinhas; os dispositivos emparelhados ficam até os remover; esta versão não guarda postmortems, incidentes nem notas.

## Pontos de controlo assinados do registo de ações

`audit_checkpoints.enabled` (desligado) assina a cadeia (HMAC-SHA256) com uma chave da instalação: `config/audit_checkpoint.key`, ou o ficheiro indicado em `MONITOR_AUDIT_KEY_FILE` para a manter à parte. Um ponto de controlo na primeira linha e depois pelo menos de hora a hora e a cada 1000 linhas; a âncora também é assinada, e um corte do fim seguido de uma linha nova fica escrito na cadeia. `python bin/monitor_cli.py audit verify` (`--audit-from N`), `audit checkpoint` e `audit purge --older-than-days N` (`--dry-run`), que remove ficheiros rodados inteiros e assina por onde a cadeia continua. Quem puder ler a chave pode assinar: mantenha-a longe de quem pode escrever o registo.

## Exportação do registo de ações

`audit_export.enabled` (desligado) com `audit_export.target` = `file` (`path`, rodado aos `max_mb`), `syslog` (`host`, `port` 6514, RFC 5424 sobre TCP com TLS, `ca_file`) ou `http` (`url`, POST de linhas JSON, token da variável indicada em `token_env`). Os endereços privados precisam de `audit_export.allow_private_targets`. O registo é a fila: o que o destino não aceitou espera ali; acima de `spool_mb` o doctor indica `system.audit_export_lag`, e as linhas rodadas antes de poderem ser enviadas contam como perdidas. `python bin/monitor_cli.py audit export` faz uma passagem agora. Testado contra recetores deste computador, não contra um produto syslog ou SIEM real.

## Versões suportadas

Só é suportada a última versão publicada: não há ramo de longo prazo. O doctor (`compliance_support`) avisa quando sabe de uma mais nova.

## Provas do reforço

`[IMP]` = um teste deste repositório exercita o controlo; `[PAR]` = só uma parte, e a linha diz o que falta. A lista é `schemas/controls.json` e um teste verifica que esta tabela e os testes indicados coincidem.

| Controlo | Estado | Nome |
|---|---|---|
| `sqlite_contention` | [IMP] | Vários processos a escrever uma base de dados |
| `storage_migrations` | [IMP] | Migrações do armazenamento |
| `retention_by_category` | [IMP] | Retenção por categoria e legal |
| `incoming_webhook` | [IMP] | Webhook de entrada: assinatura, tamanho, tempo |
| `metrics_labels` | [IMP] | Etiquetas de /metrics |
| `timezone` | [IMP] | Fusos horários e mudança da hora |
| `read_only_strict` | [IMP] | Só leitura estrita |
| `egress_policy` | [IMP] | Política de rede |
| `audit_chain` | [IMP] | Cadeia e pontos de controlo do registo |
| `service_and_volume` | [PAR] | Serviço em systemd e base grande (sistemas de ficheiros de rede por testar) |

## Limites conhecidos

- Uma conta `viewer` sentada no próprio computador do monitor é tratada como local e vê os caminhos completos.
- O webhook de entrada só verifica a janela de tempo nas entregas `workflow_run` e `workflow_job`.
- Com `none` ou `github_only`, um processo Python arrancado pelo monitor só aplica a política se importar o monitor; um programa que o utilizador execute fica de fora.
- Nesta versão não existem cifragem em repouso, ramo de longo prazo nem federação.
