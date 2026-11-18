<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Atualizar o monitor (o atualizador)

[English](UPDATE.md) · [Español](UPDATE_spa.md) · [Français](UPDATE_fra.md) · [Italiano](UPDATE_ita.md) · [Deutsch](UPDATE_deu.md) · [简体中文](UPDATE_zho.md) · [日本語](UPDATE_jpn.md) · **Português**

O atualizador leva uma instalação de qualquer versão publicada para qualquer outra (a subir ou a descer), migra a sua configuração e deixa um caminho de volta. É UM só ficheiro, `monitor_updater.py`, que só precisa de Python e funciona com qualquer versão instalada; também está dentro do produto (`tools/monitor_updater.py`) e como comando `monitor_cli.py update`. Nunca se atualiza sozinho: só quando o pede, e não apaga nada (o que é substituído vai para a pasta das cópias).

## Três formas de o abrir

- `py -3 monitor_updater.py` abre uma página no navegador. É servida em 127.0.0.1 apenas enquanto o atualizador corre, com um token de uso único no endereço; mais ninguém a pode usar.
- `py -3 monitor_updater.py --tk` abre o mesmo numa janela (precisa de Tkinter).
- `py -3 monitor_updater.py --console` é um menu de texto para servidores, SSH e contentores.
- `py -3 bin/monitor_cli.py update` é o mesmo ficheiro lançado a partir do produto; `update plan`, `update apply` e os restantes comandos abaixo aceitam as opções da tabela.

## O menu Atualizações dentro do monitor

A edição Completa tem o mesmo atualizador dentro da sua página: **Sistema > Atualizações**. Mostra a versão instalada e a que a verificação encontrou (definição `updates.check`; nada é pedido ao GitHub enquanto estiver desligada ou o monitor estiver offline), as notas de cada versão e, com o botão «Procurar versões», a lista das publicadas. Nada é descarregado nem aplicado se não carregar num botão. Aplicar exige um administrador no computador onde o monitor corre (as rotas `/api/updates/*` respondem 403 a partir da rede) e uma confirmação que diz o que vai acontecer: o SHA-256 do zip comparado com o SHA256SUMS, a cópia feita antes (com a sua pasta), a migração da configuração e o reinício. A atualização corre num processo próprio: o monitor para sozinho, a atualização é aplicada, o monitor arranca de novo com a versão nova e a página volta a ligar-se; se a versão nova não arrancar, a anterior é reposta e arrancada. «Voltar à versão anterior» faz o mesmo ao contrário. Os passos, o histórico e o resultado vêem-se na página e ficam anotados no registo de ações. Não é oferecido na edição Lite, num contentor nem sob um gestor de serviços (reiniciam o processo por conta própria: use a linha de comandos), e só corre uma atualização de cada vez. A sua configuração, os dados, as chaves e os registos não são substituídos. O ficheiro autónomo continua a ser o caminho de volta quando o monitor não arranca.

## O que faz, passo a passo As rotas que o sustentam são `/api/updates/status`, `/api/updates/progress`, `/api/updates/history` (só leitura) e `/api/updates/check`, `/api/updates/plan`, `/api/updates/apply`, `/api/updates/rollback` (administrador, só a partir deste computador).

1. Deteta a instalação: pasta, versão, edição (Completa ou Lite), configuração, dados, portas, se o monitor está em execução, contentor ou serviço.
2. Lista todas as versões publicadas no GitHub (sem token) com data e notas, e assinala a instalada e a última. Sem ligação, dê-lhe um zip com `--zip`.
3. Escolhe a versão de destino. Uma inferior é um downgrade: pede `--allow-downgrade`.
4. Mostra o PLANO como ensaio a seco: a cadeia de passos entre as duas versões (lida do registo de migrações), o que muda na SUA configuração, as mudanças de comportamento que vai notar e cada incoerência encontrada.
5. Aplica-o: cópia prévia, SHA-256 verificado com o SHA256SUMS, zip extraído para uma pasta nova e inspecionado (caminhos com `..`, ligações, tamanho), produto copiado, as suas linhas próprias dos lançadores repostas, configuração migrada, estrutura de pastas migrada e, se quiser, o monitor iniciado e `/api/health` verificado.
6. Se algo falhar volta sozinho ao estado anterior e escreve um relatório. Cada atualização fica no histórico (`update_history.jsonl`) e a última pode ser desfeita com o comando `rollback`.

## Comandos

Sem comando abre-se a página. Os comandos respondem uma vez (acrescente `--json` para um documento):

| Comando | Significado |
|---|---|
| `status` | o que está instalado e o que as verificações encontram |
| `releases` | todas as versões publicadas |
| `plan` | o ensaio a seco para um destino |
| `apply` | fazê-lo (`--dry-run` só mostra o plano) |
| `migrate` | migrar apenas um ficheiro de configuração, ver abaixo |
| `rollback` | voltar à versão anterior à última atualização |
| `history` | as atualizações feitas nesta instalação |

## Opções

| Opção | Significado |
|---|---|
| `--dir` | a instalação (por omissão, onde está o ficheiro, a procurar para cima) |
| `--to` | versão de destino (por omissão, a última) |
| `--from` | migrate: a versão de onde vem o ficheiro |
| `--config` | migrate: um ficheiro de configuração |
| `--zip` | usar este zip em vez do GitHub |
| `--sha256` | SHA-256 esperado do zip |
| `--dry-run` | só mostrar o plano |
| `--apply` | migrate: escrever o resultado |
| `--yes` | não pedir confirmação |
| `--json` | a resposta como um documento JSON |
| `--keep-old-defaults` | escreve o valor por omissão antigo de cada definição que nunca definiu, para o comportamento não mudar |
| `--adopt-new-defaults` | move também para o novo valor as definições que ainda têm o antigo |
| `--start` | iniciar o monitor depois e verificá-lo |
| `--handover` | o monitor que iniciou este processo para sozinho: esperar por ele, aplicar, arrancá-lo de novo (se o arranque falhar, volta a versão anterior) |
| `--status-file` | escreve o progresso neste ficheiro JSON (o menu Atualizações lê-o) |
| `--edition` | complete ou lite, se não se puder deduzir |
| `--allow-downgrade` | permitir uma versão inferior |
| `--allow-container` | trabalhar mesmo assim dentro de um contentor (a imagem não é substituída) |
| `--no-gh` | não usar o programa `gh`, só a API pública |
| `--backups` | pasta das cópias (por omissão, update_backups na instalação) |
| `--restore-data` | yes, no ou auto: o que o regresso faz aos dados |
| `--port` | porta da página |
| `--no-browser` | não abrir o navegador |
| `--tk` | a janela |
| `--console` | o menu de texto |
| `--lang` | idioma: en es de fr it ja zh pt |

## A sua configuração e os valores por omissão que mudam

- O registo de migrações (ficheiros JSON versionados em cada release, `assets/migrations/`) diz, para cada versão, o que mudou: definições renomeadas, removidas ou novas, novos valores por omissão, ficheiros movidos, mudanças de comportamento. O atualizador aplica a cadeia das versões que saltar.
- Por omissão conserva o que definiu explicitamente e adota um novo valor por omissão apenas onde nunca definiu a definição. Uma mudança de comportamento (por exemplo, uma função que passa a vir desligada) é indicada no relatório; `--keep-old-defaults` fixa o comportamento antigo e `--adopt-new-defaults` passa tudo para o novo.
- `migrate` trabalha sobre um ficheiro isolado: `monitor_updater.py migrate --from 2.0.1 --to 2.0.8 --config meu.json` mostra o resultado e `--apply` escreve-o (depois de uma cópia). Os segredos aparecem mascarados em qualquer relatório.

## Verificações antes de aplicar

- Bloqueiam: o monitor está em execução, o SHA-256 não coincide, o zip não é seguro, falta espaço em disco, dados de um esquema mais recente do que o destino, um contentor, outra atualização pendente.
- Avisam: definições que já não existem ou mudaram de tipo ou intervalo, valores fora do intervalo, chaves duplicadas, uma porta ocupada por outro programa, um lançador que alterou, um passo que exige outro antes. Cada aviso traz uma ação sugerida.

## Segurança e o caminho de volta

- Só escuta em 127.0.0.1 com um token efémero, recusa pedidos de outros sítios, não executa nada do zip, não usa shell e só escreve dentro da instalação e da pasta das cópias.
- Antes de alterar seja o que for copia o pacote, a configuração e os dados; se um passo falhar, a cópia é restaurada e é escrito um relatório. Se até o regresso falhar, a cópia fica intacta e o relatório explica como a restaurar à mão.
- Sem Internet: `--zip FICHEIRO` com `--sha256` (ou um SHA256SUMS ao lado). Docker: atualiza-se o volume, a imagem não é substituída por dentro (`--allow-container` para forçar).

## Códigos de saída

| Código | Significado |
|---|---|
| 0 | feito, ou nada a fazer |
| 2 | utilização incorreta |
| 3 | bloqueado por uma verificação, nada mudou |
| 4 | falhou a transferência, o SHA-256 ou o zip, nada mudou |
| 5 | falhou e o estado anterior foi restaurado |
| 6 | falhou e o regresso também falhou: restaure a cópia à mão |
| 7 | sem ligação ao GitHub e sem zip |
| 8 | não confirmado |
