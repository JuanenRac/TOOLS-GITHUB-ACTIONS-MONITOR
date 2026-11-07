<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_SCHEMA.md) | [🇪🇸 Español](CI_RED_SCHEMA_spa.md) | [🇫🇷 Français](CI_RED_SCHEMA_fra.md) | [🇮🇹 Italiano](CI_RED_SCHEMA_ita.md) | [🇩🇪 Deutsch](CI_RED_SCHEMA_deu.md) | [🇨🇳 简体中文](CI_RED_SCHEMA_zho.md) | [🇯🇵 日本語](CI_RED_SCHEMA_jpn.md) | **🇵🇹 Português**

# ci_red.json - esquema 2 (contrato estável)

`ci_red.json` é o instantâneo que o monitor escreve (de forma atómica, por predefinição ao lado de si próprio) para que qualquer consumidor possa ler o estado da CI sem perguntar
ao monitor nem ao GitHub: um painel, um script, um gancho de notificação. O formato é **estável: os campos só são acrescentados, nunca renomeados nem removidos**.
Leia-o com `.get()`; ignore os campos que não conhecer.

O local onde é escrito define-se em `actions_monitor.json`:

| chave (`sentinel.`) | significado |
|---|---|
| `ci_red_file` | `""` = `ci_red.json` ao lado do monitor (predefinição); `"off"` = não é escrito; um caminho = é escrito aí (os caminhos relativos são relativos à pasta do monitor; é recusada uma unidade D:, um caminho UNC ou uma unidade que o sistema em execução não possa usar) |
| `ci_red_audit_copy` | `true` copia-o também para a pasta de auditoria quando essa pasta existe |

## Estrutura

```json
{
  "schema": 2,
  "generated": "2026-01-01T12:00:00Z",
  "tool_version": "1.2.0",
  "complete": true,
  "red_repos": 1,
  "pending_sign_repos": 1,
  "pending_sign_hours_threshold": 24,
  "repos": {
    "REPO": {
      "ecosystem": "armor | urtc | hydra | eh3d | other",
      "red": [{"workflow": "CI", "conclusion": "failure", "since": "2026-01-01T10:00:00Z", "streak": 2, "url": "https://github.com/OWNER/REPO/actions/runs/1"}],
      "pending_sign_hours": 31.5,
      "pending_sign": [{"workflow": "firmware-build.yml", "hours": 31.5, "state": "built_on_gha | signed_local",
                         "signature_kind": "none | dev | release", "signature_verified": true,
                         "last_build_at": "2026-01-01T08:00:00Z", "url": "https://github.com/OWNER/REPO/actions/runs/2"}]
    }
  }
}
```

* `complete` é `false` enquanto a sentinela ainda está a carregar: nesse caso, não trate como verde um repositório em falta.
* `signature_verified` é `true`, `false` ou a cadeia `"unknown"` (nunca um palpite: os formatos que esta ferramenta não consegue verificar são `"unknown"`).
* Os campos `pending_sign*` descrevem o **lado da assinatura local** e destinam-se às suas próprias ferramentas locais. Um consumidor público deve ignorá-los.

## A regra do «vermelho» (uma só definição, em todo o lado)

Olha-se para a **última execução concluída de cada workflow no ramo predefinido**. Está vermelha quando a sua conclusão é `failure`, `timed_out`,
`startup_failure` ou `action_required` (aguarda uma aprovação). `cancelled`, `skipped`, `neutral` e `stale` não dizem nada e são ignoradas.
O «verde» do estado de assinatura usa a mesma lista de execuções. Um consumidor que volte a calcular a regra a partir das execuções dos workflows tem de usar exatamente esta
definição para coincidir com o monitor.

## Publicar é um passo separado e explícito

**Decisão: este PC não publica `ci_red.json` e não publica `pending_sign` nem qualquer outra parte do lado da assinatura num repositório, num painel ou em qualquer
serviço.** O ficheiro fica na máquina (e, quando `ci_red_audit_copy` está ativo, na pasta de auditoria local). Um painel público deve recalcular a lista de vermelhos a partir das
execuções públicas dos workflows com a regra acima, ou usar a exportação descrita a seguir, que nunca inclui o estado de assinatura.

Nada no monitor publica este ficheiro num repositório. Se um painel público precisar da lista de vermelhos, deixe-o recalcular a regra a partir dos
dados públicos das execuções, ou exporte você próprio a parte não sensível:

```
python3 read_report.py --export-status DIR
```

Isto escreve `ci_status_public.json` e `ci_status_public.md` na pasta que indicar e **apenas** a lista de workflows a vermelho (repositório,
ecossistema, workflow, conclusão, desde quando, sequência, ligação à execução). Sem estado de assinatura, sem nomes de chaves, sem caminhos locais, sem comandos. A ferramenta nunca faz commit nem
push; o que acontece à pasta depois fica ao seu critério.

`python3 read_report.py --export-sign-queue FILE` (`.json` ou `.csv`) escreve a fila de assinatura global com os comandos locais exatos. Esse ficheiro é
para o PC que executa o monitor e diz isso no seu interior.
