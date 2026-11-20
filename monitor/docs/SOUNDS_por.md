<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SOUNDS.md) | [🇪🇸 Español](SOUNDS_spa.md) | [🇫🇷 Français](SOUNDS_fra.md) | [🇮🇹 Italiano](SOUNDS_ita.md) | [🇩🇪 Deutsch](SOUNDS_deu.md) | [🇨🇳 简体中文](SOUNDS_zho.md) | [🇯🇵 日本語](SOUNDS_jpn.md) | **🇵🇹 Português**

# Sons

A página faz os seus próprios sons com a API Web Audio, um por cada tipo de evento, para distinguir de ouvido o que aconteceu sem olhar. Não há ficheiros de áudio: os tons são gerados no navegador, sem ligação, e não se envia nada para lado nenhum. Cada som tem também o seu aviso visual (os mosaicos, os separadores, as etiquetas); o som nunca o substitui.

| Tipo | Quando toca | O som |
|---|---|---|
| Vermelho | Um workflow que não estava vermelho passa a vermelho (uma falha nova). | Dois tons ascendentes, o clássico "bing bing". |
| Segurança ou grave | Um alerta novo da sentinela de segurança, um alerta grave (erro ou crítico) da sentinela de colaboração ou uma conta que ficou cega. | Três pulsos graves. |
| Preso | Uma compilação presa, uma fila fantasma ou um problema com os runners. | Um deslize longo descendente. |
| Pontuação | A pontuação da frota desce (`score.dropped`). | Três notas descendentes. |
| Ligação | Perde-se a ligação ao GitHub ou a desta página ao monitor. | Duas notas graves e longas. |
| Aviso | Um alerta novo de nível aviso (uma assinatura pendente, uma questão antiga, um pull request à espera). | Dois tons médios iguais. |
| Resolvido | Um workflow vermelho volta a verde ou desaparece um alerta grave. | Três notas ascendentes. |
| Relatório | Um dos relatórios opcionais mostra uma deteção que não existia. | Dois toques suaves de sino, agudo e depois mais grave. |
| Lição | As lições das falhas mostram uma categoria nova, ou uma que começa a repetir-se ou a aplicar-se. | Três notas agudas rápidas. |
| Aviso informativo | Um alerta novo de nível informativo (a versão do original de um fork, por exemplo). | Um sinal suave. |
| De novo online | A ligação ao GitHub, ou desta página com o monitor, regressa após uma quebra. | Quatro notas ascendentes. |

## Porque pode um navegador ficar mudo e o que faz a página

- Um navegador só deixa uma página tocar depois de clicar, tocar ou premir uma tecla nela. Até lá a barra mostra o aviso "Som bloqueado pelo navegador: clique aqui para o ativar". O primeiro clique em qualquer sítio desbloqueia-o.
- O que aconteceu enquanto o som estava bloqueado é guardado (dez minutos no máximo) e toca na primeira oportunidade: o clique, a página que volta ao primeiro plano ou a verificação seguinte, de dois em dois segundos. Não se perde nada entre duas leituras; o que tem mais de dez minutos é notícia velha e não é anunciado.
- A primeira leitura da página só memoriza o que já existe; um recarregamento dentro de poucas horas também o memoriza, pelo que uma falha que chegou com a página fechada é nova.
- Um separador em segundo plano mantém o som enquanto o navegador mantiver a página acordada; alguns navegadores pausam os separadores escondidos ao fim de um tempo. O melhor é deixar os ecrãs de parede e a página numa janela visível.

## Sem excesso de avisos

- Um tipo que acabou de tocar espera `sound.cooldown_seconds` (30 s por predefinição) antes de tocar de novo.
- Vários tipos na mesma leitura fazem uma única rajada: no máximo três padrões, o mais grave primeiro; o resto espera pela rajada seguinte. Duas rajadas nunca se sobrepõem.
- Um alerta silenciado (separador Alertas) nunca toca.

## A biblioteca de sons

Além dos onze sons que cada tipo de evento sempre teve, o monitor traz uma biblioteca de 54 sons (65 no total) que pode atribuir a qualquer tipo de evento. São feitos no navegador (e, para o sinal sonoro deste computador, com as mesmas notas), por isso não há ficheiros de áudio para descarregar. Os sons dos tipos são os primeiros onze; os restantes são de atribuição livre: `bell`, `chime`, `ding_dong`, `doorbell`, `ding`, `ping_high`, `ping_low`, `tick_soft`, `tock_soft`, `double_tick`, `tick_tock`, `knock`, `knock_three`, `blip`, `bloop`, `bubble`, `drop`, `droplet`, `arpeggio_up`, `arpeggio_down`, `minor_up`, `minor_down`, `fanfare`, `level_up`, `coin`, `harp_up`, `harp_down`, `marimba`, `xylophone`, `pluck`, `cascade`, `sparkle`, `ascend`, `descend`, `notify_a`, `notify_b`, `notify_c`, `sweep_up`, `sweep_down`, `whistle_up`, `whistle_down`, `zap`, `laser`, `radar`, `sonar`, `beacon`, `heartbeat`, `alarm_fast`, `siren`, `klaxon`, `buzzer`, `gong`, `phone`, `cuckoo`.

Para dar a um tipo outro som escreva pares `tipo=som` separados por vírgulas em `sound.voices`, por exemplo `new_red=coin,warning=drop`. Os tipos são `new_red`, `sentinel`, `stuck`, `score_drop`, `connection_lost`, `warning`, `resolved`, `report`, `lesson`, `info`, `live_recovered`. Um nome que não esteja na biblioteca é ignorado e o tipo mantém o seu próprio som. Os ecrãs de parede podem acrescentar a sua própria lista em `screens.sound_voices` e o seu próprio volume em `screens.sound_volume`. Nenhum som dura mais de um segundo e todos são diferentes entre si.

Dois fundos opcionais, ambos desligados por predefinição: `sound.ambient` (duas notas graves muito suaves, calmas enquanto nada está vermelho e mais ásperas enquanto algo está) e `sound.tick` (um clique seco muito curto a cada `sound.tick_seconds`, para se ouvir um ecrã congelado). Ambos seguem o chip de silêncio, o interruptor principal e o horário silencioso.

## Definições (Definições, Som)

Todas estão no ficheiro de configuração e no separador Definições; o volume, o tema e os interruptores aplicam-se logo.

| Definição | O que faz |
|---|---|
| `sound.enabled` | Interruptor geral de todos os sons da página. |
| `sound.on_new_red`, `sound.on_connection_lost`, `sound.on_warning`, `sound.on_resolved`, `sound.on_report`, `sound.on_lesson`, `sound.on_sentinel`, `sound.on_stuck`, `sound.on_score_drop`, `sound.on_info`, `sound.on_live_recovered` | Um interruptor por tipo (todos ligados por predefinição). |
| `sound.theme` | `classic` (tons claros) ou `soft` (tons mais graves, redondos e lentos). Cada tipo mantém o seu ritmo nos dois. |
| `sound.volume` | De 1 a 100, moderado por predefinição. |
| `sound.cooldown_seconds` | Pausa entre dois sons do mesmo tipo. |
| `sound.quiet_enabled`, `sound.quiet_from_hour`, `sound.quiet_to_hour` | Horário silencioso (desligado por predefinição): entre as duas horas deste computador não toca nada; pode atravessar a meia-noite. |
| `sound.server_beep` | Desativado por predefinição. O próprio monitor soa neste computador quando não há nenhuma página aberta ou o navegador bloqueia o som: um padrão para cada tipo de evento da tabela acima (tons do Windows, sons de sistema do macOS, eventos canberra no Linux), com os mesmos interruptores e horário silencioso da página, numa rajada de no máximo três tipos de cada vez; apenas local. |
| `sound.voices` | Dá a um tipo de evento outro som da biblioteca (pares `tipo=som` separados por vírgulas). Vazio por predefinição. |
| `sound.ambient`, `sound.ambient_volume` | Som ambiente (desligado por predefinição) e o seu volume, de 1 a 50. |
| `sound.tick`, `sound.tick_seconds` | Tique de relógio (desligado por predefinição) e segundos entre tiques, de 1 a 60. |
| `screens.sound_voices`, `screens.sound_volume` | O mesmo que `sound.voices`, só para os ecrãs de parede, e o seu próprio volume (0 = o de `sound.volume`). |

## Testar cada som

Em Definições, Interface, o botão "Testar som" toca o bing bing clássico e um botão por tipo toca esse tipo com o volume e o tema das definições. A etiqueta "Som" da barra inferior silencia tudo neste navegador.

## Ecrãs de parede

Os ecrãs de parede (`/screen/...`) usam os mesmos sons, com o mesmo tema, volume, interruptores e horário silencioso. Estão desligados por predefinição: `screens.sound` tem de estar ligado e a janela precisa de `?sound=on`. Um ecrã em que ninguém toca não pode receber o clique que o navegador pede: inicie o navegador do ecrã com a opção de "permitir áudio sem gesto" (no Chromium, `--autoplay-policy=no-user-gesture-required`) ou clique uma vez na janela.

## Onde fica guardado

A etiqueta de silêncio é memorizada por cada navegador; o que a página sabe da sua última leitura também fica no navegador. Dos sons não se envia nada para nenhum servidor.
