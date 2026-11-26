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

Sob um gestor de serviços a página não aplica atualizações por omissão. Se o monitor corre como serviço de UTILIZADOR do systemd (`systemctl --user`), pode ligar `updates.systemd_helper` (desligado por omissão): a página passa a oferecer a atualização e o processo que a aplica pára esse serviço, aplica a atualização e volta a arrancar o serviço, sempre com `systemctl --user` e nunca com `sudo`. Um serviço do sistema (que precisa do administrador) não é tocado e continua a ser «use a linha de comandos». O mesmo funciona na linha de comandos com `--systemd-unit UNIDADE` (`apply` e `rollback`); se o serviço não puder ser parado não se inicia nada, e se a versão nova não arrancar repõe-se a anterior e arranca-se o serviço de novo.

**Confiança.** O SHA256SUMS vem da mesma versão do GitHub que o zip, por isso sozinho só deteta uma transferência danificada ou incompleta. O que prova a origem de uma versão a partir da 2.2.0 é a sua assinatura (abaixo).

## Versões assinadas

A partir da versão 2.2.0 todas as versões são assinadas: o SHA256SUMS tem uma assinatura Ed25519 separada, o ficheiro `SHA256SUMS.ed25519.sig`, feita com a chave do projeto, cuja parte pública viaja dentro do atualizador. O atualizador verifica-a antes de descomprimir o que quer que seja. Uma versão a partir da 2.2.0 sem assinatura válida é recusada, tal como um zip assinado que seja oferecido com outra versão. Regressar a uma versão anterior, publicada sem assinatura, é permitido com um aviso. Para um zip transferido à mão, coloque `SHA256SUMS` e `SHA256SUMS.ed25519.sig` ao lado dele (com `--zip`).

Chave pública (Ed25519, hex): `380c75210e444f71bc4fe4b9aa7cb451aad5ef2592711f7dc6ba2fd7adc3d272`. A sua impressão digital SHA-256: `6d6b995655147955a1c2fb8a84a02d828606de29b36583799ada6ca5524b5d1a`.

Além do zip, uma versão inclui `monitor_updater.py`, duas listas de materiais (`github_actions_monitor.cdx.json` em CycloneDX e `github_actions_monitor.spdx.json` em SPDX), uma assinatura junto de cada ficheiro e as atestações que o GitHub faz da compilação, que se verificam com `gh attestation verify github_actions_monitor.zip --repo JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR`. A assinatura prova quem tem a chave; a atestação prova que workflow construiu o ficheiro. São duas verificações separadas.

**Rotação da chave.** Uma chave nova chega numa versão que traz a antiga e a nova durante uma sobreposição; uma chave que deixa de ser de confiança é retirada (ou marcada como revogada) numa versão posterior. O pacote cosign (`github_actions_monitor.zip.cosign.bundle`) regista a assinatura sem chave do workflow; verifica-se com `cosign verify-blob --bundle github_actions_monitor.zip.cosign.bundle --certificate-oidc-issuer https://token.actions.githubusercontent.com --certificate-identity https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/.github/workflows/release-build.yml@refs/heads/main github_actions_monitor.zip`.

## O aviso de versão nova e os comandos

Quando a verificação (`updates.check`) encontra uma versão mais nova, uma janela na edição Completa mostra o resumo das alterações no seu idioma, uma ligação para o registo e um botão para a página Atualizações (definição `updates.notify_window`, ligada por omissão). «Mais tarde» fecha-a nesta sessão do navegador; «Não avisar desta versão» silencia apenas essa versão. Nunca aparece em ecrãs de parede ou quiosque. As suas rotas são `/api/supply/update-notice` e `/api/supply/update-dismiss`.

`monitor_cli.py verify-release --folder DIR` verifica sem rede uma pasta de ficheiros de versão transferidos com SHA256SUMS e a assinatura. `monitor_cli.py keyring list|add|revoke|verify` gere as chaves públicas (`--key-id`, `--public-key`, `--key-scope`, `--expires`, `--document`); as suas chaves ficam em `keyring.json` na pasta de configuração, as chaves privadas são recusadas e a chave de publicação do projeto não se pode alterar.

## O que faz, passo a passo As rotas que o sustentam são `/api/updates/status`, `/api/updates/progress`, `/api/updates/history`, `/api/updates/log` (as últimas linhas do registo do processo, valores depois de token ou secret ocultos), `/api/updates/copies` (só leitura) e `/api/updates/check`, `/api/updates/plan`, `/api/updates/apply`, `/api/updates/rollback`, `/api/updates/discard` (administrador, só a partir deste computador). O progresso também viaja como eventos enviados pelo servidor em `/api/updates/stream` (a página usa-o enquanto corre uma atualização e volta a perguntar de segundo e meio em segundo e meio se o navegador ou a ligação não o permitirem).

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
| `copies` | as cópias da pasta de cópias: nome, estado, versões, tamanho e qual a volta atrás precisa |
| `discard` | `discard --name CÓPIA` apaga UMA cópia depois de confirmar (`--yes` salta a pergunta); a cópia da volta atrás só com `--force`; a de uma atualização em curso, nunca |
| `log` | as últimas linhas (`--lines N`, no máximo 2000) do registo do processo da última atualização, com os valores depois de token, secret ou password ocultos |

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
- A página mostra as cópias e um botão **Descartar cópia** em cada uma (pergunta antes, e duas vezes pela cópia da volta atrás), e um botão para ler o registo completo do processo da última atualização. Descartar apaga só essa cópia, nunca a instalação nem os dados, e fica anotado no histórico.
- O atualizador independente, que corre sem o monitor, tem o mesmo: a sua página no navegador (botões **Cópias** e **Registo do processo**, e **Descartar cópia** em cada cópia, com as mesmas perguntas), o seu menu de texto (opções 7 a 9) e a sua janela (Tkinter).

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

## O aviso nomeia o comando da sua forma de instalar

O aviso de uma versão mais recente (consola, Acerca de, `/api/about`) diz agora o comando exato da forma como este monitor foi instalado, no campo `command` ao lado de `channel`: o produto descompactado (`py -3 monitor/bin/monitor_cli.py update`), um gestor de serviços (`... update apply --systemd-unit <unidade>`), um contentor (`docker pull ghcr.io/juanenrac/tools-github-actions-monitor:<versão>`), pipx, uv ou uma extensão do comando `gh`. O aviso não executa nada.
## Salvaguardas do ajudante de serviço

Com `updates.systemd_helper` (ou `--systemd-unit`) o atualizador verifica agora o serviço antes de lhe tocar: uma unidade cujo diretório de trabalho e comando não apontam para ESTA pasta pertence a outra instalação e não é parada nem iniciada; uma unidade não é iniciada enquanto outra coisa (um monitor em primeiro plano) atende a sua porta; um reinício não é dado por feito enquanto o processo continuar a ser o antigo (a unidade tem de mostrar um PID novo); e `update status --systemd-unit UNIDADE` lista apenas os erros do serviço desde o último arranque. São perguntas só de leitura a `systemctl --user show` e `journalctl --user`; uma pergunta sem resposta não bloqueia nada.
