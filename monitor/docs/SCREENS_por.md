<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCREENS.md) | [🇪🇸 Español](SCREENS_spa.md) | [🇫🇷 Français](SCREENS_fra.md) | [🇮🇹 Italiano](SCREENS_ita.md) | [🇩🇪 Deutsch](SCREENS_deu.md) | [🇨🇳 简体中文](SCREENS_zho.md) | [🇯🇵 日本語](SCREENS_jpn.md) | **🇵🇹 Português**

# Ecrãs, tamanhos e orientação

A página adapta-se ao tamanho da janela, do telemóvel ao 4K, na vertical ou na horizontal, e um mesmo monitor pode servir vários ecrãs, cada um com os separadores que escolher. Nada é consultado duas vezes: todos os ecrãs leem o mesmo estado.


Para uma TV ou uma parede com texto maior, um contraste alto ou uma rotação por alguns separadores, veja [KIOSK_por.md](KIOSK_por.md).
## Endereços

- `/` - a página inteira.
- `/screen/1`, `/screen/2`, `/screen/3` - os separadores definidos para esse ecrã (`ui.screen1_tabs` ...). Abra cada um numa janela do seu próprio monitor ou televisão.
- `?orient=portrait` ou `?orient=landscape` força a disposição de uma janela; `?tabs=now,charts` e `?rotate=30` definem os separadores e os segundos entre eles numa janela.

## Definições

| Definição | O que faz |
|---|---|
| `ui.orientation` | auto segue a janela; portrait empilha os painéis numa coluna; landscape mantém a disposição lado a lado. |
| `ui.rotate_seconds` | 0 = desligado. Segundos entre os separadores de um ecrã que tem mais de um. |
| `ui.screen1_tabs` | Separadores de /screen/1, separados por vírgulas: now, al, charts, sent, sci, scol, ssec, team, fleet, repos, rep, trep, les, hist, cfg. Vazio = todos. |
| `ui.screen1_orientation` | auto, portrait ou landscape só para /screen/1. |
| `ui.screen2_tabs` | Separadores de /screen/2. |
| `ui.screen2_orientation` | Orientação de /screen/2. |
| `ui.screen3_tabs` | Separadores de /screen/3. |
| `ui.screen3_orientation` | Orientação de /screen/3. |
| `ui.now_sort` | Ordem de A acontecer agora para quem não escolheu: ecosystem, severity, age, newest, repo, event ou state. |
| `ui.alerts_sort` | Ordem do separador Alertas para quem não escolheu: server, severity, streak, class, age, newest, repo, origin ou state. |

## Ordem das listas

A secção **A acontecer agora** do primeiro separador está ordenada por ecossistema, com um título para cada um. A lista por cima da secção altera-a: ecossistema, gravidade (primeiro as bloqueadas, depois as que têm uma tarefa com falha, depois as em curso e por fim as em fila), antiguidade (a que leva mais tempo, primeiro), mais recente primeiro, repositório, disparador (push, pull_request, schedule...) e estado (em curso antes de em fila). A escolha fica guardada para cada pessoa: no modo de equipa é o servidor que a guarda com o utilizador (`GET` e `POST /api/auth/me/view`, por isso acompanha-o noutro navegador); caso contrário, é este navegador. Enquanto ninguém escolhe, a ordem é `ui.now_sort` do ficheiro de configuração (ecossistema se faltar ou estiver errado). Os botões **Expandir tudo** e **Recolher tudo** junto à lista expandem ou recolhem de uma vez todos os repositórios da secção, com qualquer ordem; a escolha é lembrada por pessoa no mesmo sítio e sobrevive a uma atualização (um repositório que abra ou feche à mão depois mantém a sua escolha).

A lista do separador **Alertas** mantém a ordem que o monitor envia até alguém escolher outra com a lista por cima: gravidade (crítico, erro, aviso, info), a maior sequência de falhas seguidas primeiro, classe (um alerta de erro ou crítico é real e vai antes dos que há que vigiar), os mais antigos primeiro, os mais recentes primeiro, repositório, origem (a sentinela que o levantou) e estado (abertos antes de silenciados). Fica guardada do mesmo modo e, enquanto ninguém escolhe, vale `ui.alerts_sort` do ficheiro de configuração (`server` se faltar ou estiver errado).

## Tamanhos testados

Um teste de navegador abre a página em cada um destes tamanhos, percorre todos os separadores e falha se houver deslocação lateral ou texto que saia da sua caixa. As janelas de 2400 px ou mais recebem um tipo de letra maior (as de 3200 px, ainda maior) em vez de uma disposição esticada; uma janela mais alta do que larga empilha os painéis.

| Tamanho | Tipo |
|---|---|
| 1920x1080 | Full HD |
| 2560x1080 | 21:9 |
| 3440x1440 | 21:9 |
| 5120x1440 | 32:9 |
| 3840x2160 | 4K |
| 1080x1920 | Full HD |
| 2160x3840 | 4K |
| 768x1024 | tablet |
| 390x844 | phone |

## Receita para um posto com dois ou três ecrãs

1. No computador que executa o monitor, ponha `ui.screen1_tabs` em `now,al`, `ui.screen2_tabs` em `charts,repos` e, para um monitor rodado, `ui.screen2_orientation` em `portrait`.
2. Abra `http://este-computador:8765/screen/1` numa janela do primeiro monitor e `/screen/2` no segundo; F11 para ecrã inteiro. A partir de outro computador, use o modo de rede com o seu token de acesso.
3. Para um ecrã de parede em que ninguém toca, dê-lhe vários separadores e ponha `ui.rotate_seconds` em 20-30.

## Ecrãs de parede: visão geral, neste momento e sentinelas

Três páginas para um monitor ou uma televisão em que ninguém toca. Não têm menu lateral nem navegação, mostram tudo numa única vista com letra grande, animam o que está vivo e fazem piscar as falhas com suavidade. Só leem: nenhum botão altera nada e nunca chamam o GitHub (mostram o que o monitor já tem).

| Endereço | O que mostra |
|---|---|
| `/screen/overview` | Anel e letra da pontuação; a frota (verdes, vermelhos, bloqueados, em espera); as últimas 24 horas e 7 dias em gráficos de área; um mapa de calor dos repositórios por hora; o que está a vermelho há mais tempo; runners e minutos; os últimos eventos; a quota do GitHub como indicador. O cartão da frota mostra também o mapa por grupos: uma barra por cada grupo da vista de frota (o mesmo agrupamento, `fleet.group_by`) com os seus repositórios a vermelho, que precisam de atenção, em ordem ou sem dados; apenas o nome do grupo e números. |
| `/screen/now` | O que acontece neste minuto: execuções em curso com progresso e duração, a fila, execuções à espera de aprovação, falhas recentes, fusões e versões publicadas, versões por publicar e uma linha em direto das últimas duas horas. |
| `/screen/sentinels` | Um cartão por cada sentinela (A1 a A12) com o seu nível, os achados em aberto, se as suas fontes são legíveis, a última varredura e um anel que acompanha a varredura; um radar animado que assinala o que está mal e os alertas por gravidade. |

### Parâmetros do endereço

Um endereço para cada monitor. Um parâmetro pode tornar uma janela mais calma ou mais pequena do que as definições permitem, nunca mais ruidosa.

| Parâmetro | Efeito |
|---|---|
| `?monitor=1` a `9` | O número que aparece junto ao título. |
| `?theme=light` (ou `dark`, `auto`, `contrast`, ou o nome de um dos dezasseis temas) | Cores de toda a janela, acima do que dizem as definições. `contrast` é branco sobre preto, para um ecrã visto de longe. |
| `?density=compact`, `normal` ou `large` | Tamanho da letra. `?scale=1.5` aumenta tudo (de 0,5 a 3). |
| `?refresh=10` | Segundos entre atualizações (de 5 a 120). |
| `?lang=de` | Idioma (en, es, de, fr, it, ja, zh, pt). |
| `?rotate=30` | A janela passa sozinha por visão geral, neste momento e sentinelas a cada 30 segundos (mínimo 5; 0 = fica num só ecrã). Com `screens.mode` = rotate já roda; isto altera o ritmo de uma janela. |
| `?jump=off` | Só com `screens.mode` = rotate: a janela roda mas nunca salta para um vermelho novo. |
| `?blink=off` | As falhas mantêm um halo fixo em vez de piscar. Não pode ativar o que `screens.blink` mantém desligado. |
| `?repo=WORD,WORD` | Apenas os repositórios cujo nome contém uma das palavras (letras, algarismos e `. _ - /`, até oito palavras). `/screen/overview` e `/screen/now` mantêm apenas os repositórios cujo nome o ecrã mostra (um nome oculto nunca corresponde), os números seguem as linhas mantidas, e a pontuação e o mapa de grupos, que pertencem a toda a frota, não são mostrados; `/screen/sentinels` não é filtrado. |
| `?sound=on` | Um sinal sonoro curto a cada falha nova, só se `screens.sound` o permitir. Desativado por defeito. |

### Idioma dos ecrãs

O idioma de um ecrã decide-se por esta ordem: `?lang=xx` no endereço; depois o idioma escolhido na página principal do mesmo navegador (fica lá guardado, e um ecrã aberto nesse navegador lê-o, pelo que o ecrã acompanha a página sem qualquer parâmetro); depois o idioma do monitor (`MONITOR_LANG`, ou o configurado). Um ecrã cujo idioma guardado difere daquele em que foi servido volta a carregar uma vez, antes de desenhar, com `?lang=` acrescentado e os restantes parâmetros (entre eles `?rotate=`) mantidos. Os oito idiomas (en, es, de, fr, it, ja, zh, pt) são os mesmos da página: títulos, etiquetas, estados, gravidades, unidades e tempos relativos («há 5 min») vêm do catálogo, e a hora, a data e os números escrevem-se com a configuração regional do idioma (en-GB, es-ES, de-DE, fr-FR, it-IT, ja-JP, zh-CN, pt-PT). A ligação «Abrir ecrã» das Definições já leva `?lang=` com o idioma da página. Um computador que não escolhe idioma por si fica em inglês: o idioma do navegador não decide.

### Definições dos ecrãs de parede

| Definição | O que faz |
|---|---|
| `screens.enabled` | Ativa as três páginas. Desativado: `/screen/overview`, `/screen/now`, `/screen/sentinels` e `/api/screens/data` respondem 404 (`/screen/1` a `/screen/3` são a própria página e não dependem disto). A edição lite também serve os ecrãs de parede, com o ecrã dos sentinelas vazio. Desativado por defeito. |
| `screens.default_theme` | inherit (por omissão: o tema escolhido para todo o produto, ver abaixo), auto, light, dark, um dos dezasseis temas ou contrast. |
| `screens.default_density` | compact, normal (por defeito) ou large. |
| `screens.refresh_seconds` | Segundos entre atualizações de uma janela (10 por defeito). As páginas leem do monitor, nunca do GitHub, por isso um tempo curto não gasta quota. |
| `screens.rotate_seconds` | Só com `screens.mode` = three. 0 (por omissão) = sem rotação; a partir de 5, uma janela passa pelas três páginas. |
| `screens.blink` | As falhas piscam suavemente (ativado por defeito). |
| `screens.blink_calm_minutes` | Minutos após os quais uma falha a que ninguém atende mantém um halo fixo em vez de piscar (30 por defeito; 0 = pisca até ser resolvida). |
| `screens.sound` | Um sinal sonoro a cada falha nova (desativado por defeito). |
| `screens.burn_in_protection` | Desloca tudo alguns píxeis a cada minuto (ativado por defeito). |
| `screens.night_dim` | Escurece os ecrãs entre `screens.night_dim_from_hour` (22) e `screens.night_dim_to_hour` (7); desativado por defeito. |
| `screens.show_repo_names` | all, public (por defeito: os repositórios privados aparecem como private-1, private-2...) ou none (todos os nomes ficam ocultos). Use public ou none num ecrã que outras pessoas possam ver. Com uma lista de repositórios escrita à mão em `repos`, a visibilidade é lida com uma listagem da conta a cada `discover_refresh_seconds`; um repositório cuja visibilidade não pôde ser lida conta como privado. Os números (private-1...) só se dão aos repositórios ocultos, pela ordem de um HMAC do nome com uma chave da instalação guardada num ficheiro privado da pasta de dados, pelo que nada dizem sobre onde um repositório cai entre os outros. |
| `screens.theme_overview`, `screens.theme_now`, `screens.theme_sentinels` | O tema de um ecrã: inherit (por omissão: o de `screens.default_theme`) ou qualquer um dos temas acima. |
| `screens.mode` | three (por omissão: as três páginas separadas, uma por janela) ou rotate (uma só página que passa pelas três e salta para um vermelho novo). |
| `screens.rotate_every_seconds` | No modo rotate, segundos em cada ecrã (20 por omissão; de 5 a 300). |
| `screens.alert_hold_seconds` | No modo rotate, segundos que um vermelho novo mantém a janela no seu ecrã (30 por omissão; de 5 a 600), ou até o vermelho desaparecer. |
| `screens.logo_overview`, `screens.logo_now`, `screens.logo_sentinels` | Em que ecrãs aparece o logótipo (por omissão, só na visão geral). |
| `screens.logo_corner` | top-right (por omissão), top-left, bottom-right ou bottom-left. |
| `screens.logo_max_width`, `screens.logo_max_height` | Tamanho máximo do logótipo em píxeis a 1920 x 1080 (160 x 64 por omissão; cresce com o ecrã). |
| `screens.group_map` | Ativado por predefinição. Mostra o mapa da frota por grupos no ecrã geral (o agrupamento da vista de frota). Desativado: só os quatro mosaicos. |
| `screens.menu` | Ativado por predefinição. O botão Ecrãs da barra superior. Desativado: o botão desaparece; os ecrãs continuam a funcionar nos seus próprios endereços. |
| `screens.menu_target` | new (predefinição): um ecrã abre numa nova janela ou separador; same: no separador atual. |
| `screens.menu_max_windows` | Máximo de janelas que um conjunto multiecrã abre de uma vez (4 por predefinição; de 1 a 9). |
| `screens.menu_rotate_seconds` | Segundos por ecrã nas predefinições rotativas do menu (20 por predefinição; de 5 a 300). |
| `screens.menu_tv_scale` | O `?scale=` da predefinição de TV (1,5 por predefinição; de 0,5 a 3). |

### Tema dos ecrãs

Tudo o que o monitor mostra usa o tema escolhido nas Definições (`ui.theme`: auto, light, dark ou um dos dezasseis temas): a página, os ecrãs de parede e a página de início de sessão. Ao escolher um tema no seletor do separador Este navegador, ele também é guardado como `ui.theme`, pelo que um navegador que nunca escolheu fica com o do monitor. Os relatórios HTML escritos em disco seguem a definição clara ou escura do computador que os abre.

Os ecrãs de parede herdam-no: `screens.default_theme` é `inherit` por omissão. Defina-o para outro tema para fixar o mesmo em todos os ecrãs, e `screens.theme_overview`, `screens.theme_now` ou `screens.theme_sentinels` para dar a um ecrã o seu próprio tema. O endereço ainda pode fixar uma janela com `?theme=`. Nenhum ecrã escreve uma cor própria: todos usam as paletas do tema, pelo que um tema acrescentado à página aparece também nos ecrãs.

### Modo dos ecrãs: três ou rotação

`screens.mode` = three (por omissão) mantém as três páginas separadas, uma por janela. `screens.mode` = rotate faz de cada janela um só ecrã que passa por visão geral, neste momento e sentinelas a cada `screens.rotate_every_seconds` segundos (20 por omissão; de 5 a 300).

Uma falha a vermelho faz a janela saltar para o ecrã que a mostra: **Neste momento** para um workflow que falhou, **Sentinelas** para um painel de sentinela que fica vermelho. A janela fica aí `screens.alert_hold_seconds` segundos (30 por omissão; de 5 a 600) ou até esse vermelho desaparecer, o que acontecer primeiro, e depois continua a rodar. Um vermelho já mostrado não volta a fazer a janela saltar até mudar ou reaparecer. O que está vermelho quando a janela abre é apenas o ponto de partida e não a faz saltar. Se chegar um segundo vermelho enquanto a janela mantém o primeiro, espera a sua vez. Para o saber, a janela lê os outros dois ecrãs em segundo plano com a mesma chamada só de leitura (nunca o GitHub). `?rotate=0` mantém uma janela no seu ecrã e `?jump=off` mantém a rotação sem os saltos. Cada ecrã aplica o seu próprio tema e o seu próprio logótipo ao aparecer.

### Logótipo da organização

O separador Este navegador das Definições tem um bloco para carregar o logótipo da sua organização: PNG, JPEG, WebP ou SVG, no máximo 1 MB. O monitor verifica o tipo real pelos primeiros bytes do ficheiro (o nome e a etiqueta que o acompanha não contam), recusa um SVG com scripts, manipuladores de eventos, ligações a outros ficheiros ou endereços ou um tipo de documento, e guarda a imagem na pasta `data/` deste computador como `org_logo` com a sua extensão, nunca na configuração. Só existe um logótipo: carregar outro substitui-o. O registo de ações anota o carregamento e a remoção, nunca o ficheiro.

`screens.logo_overview`, `screens.logo_now` e `screens.logo_sentinels` escolhem em que ecrãs de parede aparece (por omissão, só na visão geral), `screens.logo_corner` o canto (cima à direita por omissão) e `screens.logo_max_width` e `screens.logo_max_height` o tamanho máximo em píxeis a 1920 x 1080 (160 x 64 por omissão; o logótipo cresce com o ecrã). A imagem ajusta-se a esse tamanho sem se deformar e tem um lugar próprio no cabeçalho ou no rodapé, pelo que nunca tapa o conteúdo. O fundo mantém-se transparente: um logótipo com fundo transparente fica bem nos temas claros e nos escuros.

### O que mostram e o que ocultam

Os dados vêm de `/api/screens/data?screen=overview` (ou `now`, `sentinels`): uma lista fechada de campos construída com o último ciclo, o instantâneo das sentinelas, os alertas e a pontuação. Nunca contém uma ligação, um título de commit, o nome de um job, o nome de uma pessoa nem um caminho deste computador, e os nomes dos workflows dos repositórios ocultos também ficam ocultos. No modo de rede as páginas precisam do mesmo token de acesso que o resto do monitor e a resposta é só de leitura.

### Como se comportam

- As falhas piscam menos de duas vezes por segundo (nunca de forma estroboscópica); uma falha nova faz um único clarão; uma falha a que ninguém atende durante `screens.blink_calm_minutes` minutos mantém um halo fixo. Com a definição do sistema para reduzir o movimento, ou com `?blink=off`, nada pisca nem se move. Uma falha nunca é mostrada apenas pela cor: leva um símbolo e uma palavra.
- Quando o monitor não responde, a página di-lo, escurece e tenta de novo após 5, 10, 20... segundos (até 60).
- Um ecrã sempre ligado é protegido contra a retenção de imagem: tudo se desloca alguns píxeis a cada minuto e a página pode escurecer à noite.

### Montar vários monitores

1. Escolha um endereço para cada monitor, por exemplo `/screen/overview?monitor=1`, `/screen/now?monitor=2` e `/screen/sentinels?monitor=3`; ou abra uma única janela com `?rotate=20`.
2. Abra cada um no Chrome ou no Edge em modo quiosque: `msedge --kiosk "http://este-computador:8765/screen/now?monitor=2" --edge-kiosk-type=fullscreen` ou `chrome --kiosk "http://este-computador:8765/screen/now?monitor=2"`; com `--app=ENDEREÇO` em vez de `--kiosk` a janela não tem barras. Sem modo quiosque, o botão discreto no fim da página pede o ecrã inteiro.
3. A partir de outro computador use o modo de rede: basta o token de acesso de um visualizador, porque estas páginas nunca escrevem.

## Que separador está em que ecrã de parede

Cada separador da página tem uma decisão, escrita no código (`TAB_DECISIONS` de `screens.py`) e verificada por um teste: é mostrado num dos ecrãs de parede ou diz porque não. Um separador mostrado tem os seus dados na resposta de `/api/screens/data` (a visão geral leva Alertas, Gráficos e Frota; Neste momento leva Agora; Sentinelas leva os cartões dos separadores das sentinelas). Um separador que não é mostrado indica o seu motivo:

- `people`: nomeia pessoas, e um ecrã de parede nunca mostra um nome de utilizador.
- `controls`: é feito de botões e campos que mudam alguma coisa, e um ecrã de parede não tem nenhum.
- `reading`: foi feito para ser lido, comparado ou guardado, não para ser visto ao longe.
- `text`: é feito de títulos, causas e mensagens, que um ecrã de parede nunca mostra.

| Separador | Nome | Ecrã de parede | Motivo |
|---|---|---|---|
| `now` | Agora | `/screen/now` | - |
| `al` | Alertas | `/screen/overview` | - |
| `charts` | Gráficos | `/screen/overview` | - |
| `sent` | Resumo | `/screen/sentinels` | - |
| `sci` | Sentinela de CI | `/screen/sentinels` | - |
| `scol` | Sentinela de colaboração | `/screen/sentinels` | - |
| `ssec` | Sentinela de segurança | `/screen/sentinels` | - |
| `sdel` | Sentinela de entrega | `/screen/sentinels` | - |
| `ssup` | Sentinela da cadeia de fornecimento | `/screen/sentinels` | - |
| `strend` | Tendência diária | - | `reading` |
| `syvt` | Ontem vs hoje | - | `reading` |
| `team` | Saúde da equipa | - | `people` |
| `fleet` | Frota | `/screen/overview` | - |
| `repos` | Repositórios | - | `controls` |
| `rep` | Relatórios | - | `reading` |
| `trep` | Relatórios agendados | - | `reading` |
| `les` | Lições | - | `text` |
| `hist` | Histórico | - | `text` |
| `upd` | Atualizações | - | `controls` |
| `cfg` | Definições | - | `controls` |

## Menu Ecrãs

O botão **Ecrãs** da barra superior (o ícone de dois monitores) abre um menu com todos os tipos de ecrã que o monitor tem, para que ninguém tenha de decorar os endereços. Apenas navega: abre endereços, não escreve nada e não lê nada do GitHub. Está ativado por predefinição e `screens.menu` desativa-o.

| Ecrã | Endereço | O que é |
|---|---|---|
| Painel | `/` | A página completa, para uma pessoa à secretária. `?repo=` filtra os repositórios. |
| Quiosque | `/?chrome=0&view=now` | Uma vista sem cabeçalho, separadores nem filtros, para um monitor que ninguém toca. A vista é um parâmetro. |
| Vista de equipa | `/?chrome=0&view=team` | A vista de equipa como quiosque (edição completa). |
| Ecrãs de separadores 1 a 3 | `/screen/1`, `/screen/2`, `/screen/3` | Os separadores definidos para cada monitor de uma secretária; `?tabs=`, `?orient=` e `?rotate=` alteram-nos para uma janela. |
| Ecrãs de parede | `/screen/overview`, `/screen/now`, `/screen/sentinels` | Os três ecrãs de parede descritos acima. |
| Parede rotativa | `/screen/overview?rotate=20` | Uma janela que roda pelos três e salta para um novo vermelho. |
| TV | `/screen/overview?theme=contrast&density=large&scale=1.5&rotate=20` | A parede rotativa para um ecrã visto de longe. |
| Vários monitores | um endereço por janela | Um conjunto de janelas, uma por monitor (ver abaixo). |

Cada cartão mostra os parâmetros que esse endereço aceita (tema, densidade, atualização, escala, idioma, rotação, filtro de repositórios...), cada um com o seu próprio texto de ajuda, e o endereço resultante. **Abrir** abre-o numa nova janela ou separador, ou no separador atual, conforme `screens.menu_target`; **Copiar endereço** coloca o endereço completo na área de transferência para o abrir noutro computador (nunca inclui um token: no modo de rede esse computador inicia sessão como de costume). Os ecrãs de parede respondem 404 enquanto `screens.enabled` está desativado, por isso o seu cartão di-lo em vez de abrir uma página vazia; a vista de equipa não existe na edição lite.

### Vários monitores

Escolha quantas janelas (no máximo `screens.menu_max_windows`), a distribuição (em fila, em coluna ou em grelha) e o que cada janela mostra (os três ecrãs de parede por turnos, paredes que rodam sozinhas ou os ecrãs de separadores). **Abrir todas as janelas** abre uma janela por monitor. Num navegador com a API de gestão de janelas (o Chrome e o Edge pedem a permissão *gestão de janelas*) cada janela é colocada no seu próprio monitor, ordenados como a distribuição indica; com mais janelas do que monitores partilham um monitor em mosaico. Sem ela, as janelas abrem onde o navegador as põe e o cartão lista um comando de quiosque por janela (`msedge --kiosk ENDEREÇO --window-position=X,Y`) para as iniciar à mão. O navegador tem de permitir as janelas pop-up para o endereço do monitor.

O mesmo catálogo é lido pelas ferramentas: `GET /api/screens/menu`, `monitor_cli.py screens [list|urls]` e a ferramenta MCP `screens_menu`. As três são só de leitura.

## Imagens

O separador Agora em quatro tamanhos, com dados inventados (4K, um monitor 21:9, um monitor rodado, um telemóvel):

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![ultrawide 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![rodado 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![telemóvel 390x844](../../docs/screenshots/web_size_phone_light.png)

Os três ecrãs de parede em 4K e num monitor na vertical, com dados inventados:

![Visão geral 4K 3840x2160](../../docs/screenshots/web_screen_overview_4k.png)

![Visão geral 1080x1920](../../docs/screenshots/web_screen_overview_portrait.png)

![Neste momento 4K 3840x2160](../../docs/screenshots/web_screen_now_4k.png)

![Neste momento 1080x1920](../../docs/screenshots/web_screen_now_portrait.png)

![Sentinelas 4K 3840x2160](../../docs/screenshots/web_screen_sentinels_4k.png)

![Sentinelas 1080x1920](../../docs/screenshots/web_screen_sentinels_portrait.png)

Os ecrãs de parede com outros temas, com o logótipo de uma organização e a janela que roda sozinha, com dados inventados:

![Visão geral, tema claro](../../docs/screenshots/web_screen_overview_light.png)

![Visão geral com o logótipo e o tema Midnight](../../docs/screenshots/web_screen_overview_midnight.png)

![Sentinelas, contraste elevado](../../docs/screenshots/web_screen_sentinels_contrast.png)

![A janela que roda pelos três ecrãs](../../docs/screenshots/web_screen_rotate.png)
