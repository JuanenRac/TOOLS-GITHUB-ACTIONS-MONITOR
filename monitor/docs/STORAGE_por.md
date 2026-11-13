<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](STORAGE.md) | [🇪🇸 Español](STORAGE_spa.md) | [🇫🇷 Français](STORAGE_fra.md) | [🇮🇹 Italiano](STORAGE_ita.md) | [🇩🇪 Deutsch](STORAGE_deu.md) | [🇨🇳 简体中文](STORAGE_zho.md) | [🇯🇵 日本語](STORAGE_jpn.md) | **🇵🇹 Português**

# Armazenamento e retenção

Onde a edição completa guarda o que aprende, como o mudar e o que remove por si própria. A edição lite guarda sempre ficheiros simples, não tem base de dados nem tarefa de retenção e não mostra nada disto.

## O que é guardado

Por cada conta: a configuração (`actions_monitor.json`), o estado das sentinelas, o feed de eventos, o que o feed já anunciou, as amostras de análises, os silenciamentos e o aviso de atualização. Para toda a instalação: utilizadores, as contas que podem ver e as suas sessões (o modo de equipa usa-as). As caches de leituras condicionais e os registos são sempre ficheiros simples.

## Os dois armazenamentos

|  | `file` (predefinido) | `sqlite` |
|---|---|---|
| Onde | `accounts/<id>/` (junto dos lançadores se não houver `accounts/`) | `accounts/<id>/storage.sqlite3`, uma base de dados por conta |
| Escritas | um ficheiro temporário, gravado no disco e renomeado | uma transação curta, diário WAL |
| Escolha-o para | uma pessoa; ficheiros que pode ler e editar | um serviço que corre durante meses; muitos eventos |

Escolhe-se na configuração da conta (ou do monitor): `"storage": {"backend": "sqlite"}`. A configuração em si é sempre um ficheiro JSON, porque é ela que indica o armazenamento. Com SQLite o feed de eventos está na base de dados, não em `events_monitor.jsonl`. Uma base de dados que não se consegue abrir impede o arranque: o monitor nunca escreve o seu estado noutro sítio nas suas costas.

## Decisão: um armazenamento por conta (modelo A)

*Contexto.* A edição completa executa um processo por conta. *Decisão.* Cada processo tem o seu próprio armazenamento: os seus ficheiros, ou a sua própria base de dados `storage.sqlite3` dentro de `accounts/<id>/`. Dois processos nunca escrevem o mesmo ficheiro, por isso não há nada a bloquear entre eles e um problema numa conta não pode danificar outra. *Custo.* Uma consulta entre contas obriga a ler várias bases de dados.

*Preparado: modelo B, uma base de dados partilhada.* Ponha o mesmo caminho no bloco `storage` de todas as contas (`"path": "/data/monitor.sqlite3"`). Funciona porque cada tabela leva a conta, o WAL deixa a página ler enquanto as sentinelas escrevem, as transações são curtas e, se a base estiver ocupada, espera-se até 5 segundos. Está testado (dois processos a fazer o ciclo ao mesmo tempo; uma página que responde por HTTP enquanto escrevem), mas não é o predefinido: é mais frágil do que o A e só compensa se precisar de SQL entre contas.

## O que está garantido

- Uma escrita é atómica: quem lê vê o valor antigo ou o novo. Um processo terminado a meio (`kill -9`) deixa o valor antigo; com SQLite o arranque seguinte recupera sozinho.
- O esquema tem versão (`schema_version`). Cada migração corre numa única transação, juntamente com a subida da versão, pelo que uma interrompida deixa a base como estava e repete-se no arranque seguinte. Uma base escrita por uma versão mais recente é recusada, nunca é revertida.
- Um elemento danificado ou em falta lê-se como vazio: o monitor arranca com o que houver no disco.

## Mover dados e cópias de segurança

```
python tools/migrate_storage.py --from file --to sqlite              # simulação: mostra o que copiaria
python tools/migrate_storage.py --from file --to sqlite --apply      # copia e depois compara cada elemento e cada evento
python tools/backup_storage.py backup backup.zip --backend sqlite    # um .zip com manifesto e SHA-256
python tools/backup_storage.py verify backup.zip
python tools/backup_storage.py restore backup.zip --backend file     # para um armazenamento vazio (--force sobre contas existentes)
```

A migração nunca altera nem apaga os seus ficheiros, retoma após uma interrupção (uma conta é copiada inteira ou não é copiada) e termina com falha se os dois lados diferirem; só então mude o armazenamento e reinicie. Uma cópia feita a partir de ficheiros restaura-se em SQLite e vice-versa. `--db FILE` escolhe a base partilhada do modelo B; `--flat` é a instalação sem `accounts/`. O `--doctor` verifica a base de dados (existe, integridade, esquema) sem a alterar.

## Retenção

Um monitor deixado a correr durante meses cresceria sem teto, por isso uma passagem curta no fim de uma atualização (a cada `retention.interval_hours`, 24 por omissão) remove o que é antigo:

| Definição | Predefinição | Significado |
|---|---|---|
| `retention.enabled` | ligado | o interruptor |
| `retention.events_days` | 90 | os eventos mais antigos do que isto são removidos |
| `retention.analytics_days` | 180 | os dias do histórico de análises mais antigos do que isto são removidos |
| `retention.mode` | `archive` | `archive` escreve primeiro os eventos antigos num `.gz` em `events/archive/` |
| `retention.events_max_kb` | 512 | teto de tamanho do ficheiro do feed com o armazenamento em ficheiros (como sempre) |
| `retention.warn_events_mb` | 20 | o `--doctor` avisa acima deste tamanho |

A limpeza só toca em eventos e dias de análises mais antigos do que o respetivo limite; nunca toca na configuração, no estado das sentinelas, nos silenciamentos nem num evento sem hora. Cada passagem deixa uma linha no documento de auditoria (quando, quantos eventos removidos e mantidos, o ficheiro de arquivo, quantos dias de análises, o erro se houver). O `--doctor` avisa do tamanho dos eventos e, num monitor que corre como serviço (modo de rede, sem navegador, um contentor ou `MONITOR_SERVICE=1`), quando a sua configuração não tem bloco `retention`. Faça uma cópia antes de encurtar os limites.

O predefinido `archive` guarda o que é removido em ficheiros comprimidos que pode voltar a ler; `delete` remove-o definitivamente.
