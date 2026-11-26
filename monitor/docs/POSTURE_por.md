<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](POSTURE.md) | [🇪🇸 Español](POSTURE_spa.md) | [🇫🇷 Français](POSTURE_fra.md) | [🇮🇹 Italiano](POSTURE_ita.md) | [🇩🇪 Deutsch](POSTURE_deu.md) | [🇨🇳 简体中文](POSTURE_zho.md) | [🇯🇵 日本語](POSTURE_jpn.md) | **🇵🇹 Português**

# Postura dos repositórios e da organização

Uma lista de verificações, só de leitura, sobre a proteção dos seus repositórios e organização: webhooks, definições do Actions, análises, ramos, chaves de implementação, idade dos segredos, aplicações e versões. Nada é alterado no GitHub. Edições Complete e Full; desligada por predefinição.

## Ativação

Ligue `posture.enabled` (Definições > Postura). São lidos poucos repositórios por ciclo (`posture.repos_per_cycle`), cada um no máximo a cada `posture.refresh_hours`; consome quota do GitHub. `posture.org_checks` acrescenta a organização.

## O que é verificado

Cada constatação indica o seu lugar nos riscos OWASP Top 10 CI/CD e no guia CIS da cadeia de fornecimento. A correspondência ajuda a ler; não é uma certificação.

| Área | Identificadores |
|---|---|
| Entregas de webhooks | webhook.no_secret webhook.plain_http webhook.tls_off |
| Definições do Actions | actions.token_write actions.approves_prs actions.all_allowed actions.sha_not_required actions.fork_approval |
| Código e dependências | scan.no_code scan.no_credentials scan.no_push_protection scan.no_dependency_alerts repo.no_policy repo.no_update_tool |
| Ramos | branch.unprotected branch.no_review branch.bypass branch.release_unprotected branch.merged_unreviewed |
| Chaves e segredos | deploy.write deploy.old stored.old |
| Organização | org.no_two_factor org.default_write org.public_creation org.app_broad org.settings_changed org.pat_broad |
| Executores | runner.not_hardened runner.coverage_lost |
| Versões | release.asset_replaced release.asset_removed release.tag_moved release.outside_window |

## Cobertura honesta

O que o GitHub recusa ou não responde aparece como **por verificar**, nunca como correto, e as constatações anteriores dessa área mantêm-se. Muitas definições exigem leitura de administração: o relatório indica a permissão de cada grupo e as recusadas. De um webhook só se guarda o anfitrião; de um segredo, o nome e as datas. As versões são comparadas com o visto antes, por isso a primeira leitura apenas memoriza. Repositórios arquivados e forks são ignorados.

## Referência e opções

`posture.profile` é basic ou strict. `posture.types` atribui a padrões um tipo (`standard`, `library`, `internal`, `sandbox`) com a sua referência; `posture.skip` exclui verificações. `posture.release_branches` são padrões de ramos a proteger. `posture.deploy_max_days` e `posture.stored_max_days` fixam idades. Desligados até serem pedidos: `posture.audit_log` (auditoria da organização, GitHub Enterprise), `posture.review_sample` (alterações integradas sem aprovação), `posture.runner_runs` (passo de reforço realmente executado). `posture.releases` vigia ficheiros substituídos e etiquetas movidas; `posture.release_window` fixa o horário.

## Onde ver

O separador Segurança das sentinelas mostra as constatações, a maturidade da cadeia de segurança de cada repositório, um histórico diário e as permissões. `posture.alerts` leva cada constatação aos Alertas, onde pode ser silenciada. API: `GET /api/posture`. Linha de comandos:

```
posture status
posture matrix
posture check --repo-name my-repo
posture report
```

## Limites

Por fazer: uma segunda GitHub App de escrita (leitura e escrita não estão divididas por duas Apps). `org.pat_broad` precisa de uma GitHub App com a permissão de tokens de acesso pessoal; com um token pessoal não é verificado. As verificações de organização só foram testadas com respostas inventadas.

## Relatório de conformidade e permissões

`posture report` (e `compliance` em `GET /api/posture`) lê as constatações face aos dez riscos OWASP de CI/CD e às secções CIS correspondentes: com constatações, sem constatações, lido em parte ou não verificado, com um texto curto sobre o que significa cada risco e a tendência face a uma semana antes. É uma ajuda de leitura, não uma certificação; os números de secção CIS não foram confrontados com o documento oficial. `upstream.weak` (`posture.upstream`, desligado) assinala um fork cujo original público não tem política de segurança ou ferramenta de atualização. A tabela de permissões diz que permissão de GitHub App desbloqueia cada grupo e, com uma App configurada, se está concedida.
