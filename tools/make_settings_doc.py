#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/make_settings_doc.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Writes the "what can be changed" part of monitor/docs/SETTINGS*.md (the eight languages) from the schema of the Settings tab and the texts of the page.

    python tools/make_settings_doc.py            # rewrites the marked part of the eight files
    python tools/make_settings_doc.py --check    # exit 1 when a file is out of date

The tab names, the block titles and the labels are the very texts of monitor/assets/locales/*.json, so the guide always uses the words of the page.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MON = ROOT / "monitor"
sys.path.insert(0, str(MON / "src"))
from github_actions_monitor.app import settings_api as sa  # noqa: E402

BEGIN, END = "<!-- settings:begin -->", "<!-- settings:end -->"
FILES = {"en": "SETTINGS.md", "es": "SETTINGS_spa.md", "de": "SETTINGS_deu.md", "fr": "SETTINGS_fra.md", "it": "SETTINGS_ita.md", "ja": "SETTINGS_jpn.md", "zh": "SETTINGS_zho.md", "pt": "SETTINGS_por.md"}
TEXT = {
    "en": ("What can be changed", "Only the keys of the list in `settings_api.py` (the schema). Each one has a type and a range, and the page says whether a change needs a **restart** of the monitor (the loop reads its configuration once) or **applies now**.",
           "The tab is split into sub-tabs, ordered from the common to the advanced: This browser, Basic, General, Refresh and limits, Sentinel, Surface checks (A10), Readiness (A11), Folders and files, Outputs, then the integrations. Inside a sub-tab the settings are grouped in titled blocks; the first field of a block is its main switch and, while it is off, the rest of the block is dimmed and cannot be edited. Every field shows its unit (s, min, h, days, MB, calls), its range, a badge (needs a restart / applies now), a badge for the safety options that start in their conservative state, and one line of help. The search box filters the settings of all the sub-tabs; each sub-tab counts its unsaved changes; the Save and Discard buttons stay visible; the sub-tab you used last is remembered by the browser. The tabs follow the keyboard pattern of tabs (arrow keys, Home, End).",
           "Tab", "Blocks and settings", "This browser", "language of the page, theme (auto / light / dark), dense view of the Now tab. These are kept in the browser, not in the file.",
           "A setting appears in one place only. Read-only: `webhook.signing_state` only says whether the shared secret is defined; the secret itself is never shown."),
    "es": ("Qué se puede cambiar", "Solo las claves de la lista de `settings_api.py` (el esquema). Cada una tiene un tipo y un rango, y la página dice si un cambio necesita **reiniciar** el monitor (el bucle lee su configuración una vez) o **se aplica ya**.",
           "La pestaña se divide en subpestañas, ordenadas de lo común a lo avanzado: Este navegador, Básico, General, Refresco y límites, Centinela, Comprobaciones de superficie (A10), Preparación (A11), Carpetas y archivos, Salidas y después las integraciones. Dentro de cada subpestaña los ajustes van en bloques con título; el primer campo de un bloque es su interruptor principal y, mientras está apagado, el resto del bloque se atenúa y no se puede editar. Cada campo muestra su unidad (s, min, h, días, MB, llamadas), su rango, una insignia (pide reinicio / se aplica ya), otra para las opciones de seguridad que arrancan en su estado conservador y una línea de ayuda. El buscador filtra los ajustes de todas las subpestañas; cada subpestaña cuenta sus cambios sin guardar; los botones Guardar y Descartar siempre están visibles; el navegador recuerda la última subpestaña. Las pestañas siguen el patrón de teclado de las pestañas (flechas, Inicio, Fin).",
           "Pestaña", "Bloques y ajustes", "Este navegador", "idioma de la página, tema (auto / claro / oscuro), vista densa de la pestaña Ahora. Se guardan en el navegador, no en el archivo.",
           "Cada ajuste aparece en un solo sitio. Solo lectura: `webhook.signing_state` únicamente dice si el secreto compartido está definido; el secreto nunca se muestra."),
    "de": ("Was sich ändern lässt", "Nur die Schlüssel der Liste in `settings_api.py` (das Schema). Jeder hat Typ und Bereich, und die Seite sagt, ob eine Änderung einen **Neustart** des Monitors braucht (die Schleife liest ihre Konfiguration einmal) oder **sofort gilt**.",
           "Der Reiter ist in Unterreiter gegliedert, vom Gewöhnlichen zum Fortgeschrittenen: Dieser Browser, Grundlagen, Allgemein, Aktualisierung und Grenzen, Wächter, Oberflächenprüfungen (A10), Bereitschaft (A11), Ordner und Dateien, Ausgaben, danach die Integrationen. In einem Unterreiter stehen die Einstellungen in Blöcken mit Titel; das erste Feld eines Blocks ist sein Hauptschalter, und solange er aus ist, ist der Rest des Blocks abgedunkelt und nicht editierbar. Jedes Feld zeigt Einheit (s, Min., Std., Tage, MB, Aufrufe), Bereich, ein Abzeichen (braucht Neustart / gilt sofort), ein Abzeichen für Sicherheitsoptionen mit konservativem Standard und eine Hilfezeile. Das Suchfeld filtert die Einstellungen aller Unterreiter; jeder Unterreiter zählt seine ungespeicherten Änderungen; Speichern und Verwerfen bleiben sichtbar; der Browser merkt sich den zuletzt benutzten Unterreiter. Die Reiter folgen dem Tastaturmuster für Reiter (Pfeiltasten, Pos1, Ende).",
           "Reiter", "Blöcke und Einstellungen", "Dieser Browser", "Sprache der Seite, Design (auto / hell / dunkel), dichte Ansicht des Reiters Jetzt. Sie bleiben im Browser, nicht in der Datei.",
           "Jede Einstellung steht nur an einer Stelle. Nur lesend: `webhook.signing_state` sagt nur, ob das gemeinsame Geheimnis definiert ist; das Geheimnis selbst wird nie angezeigt."),
    "fr": ("Ce qui peut être modifié", "Seulement les clés de la liste de `settings_api.py` (le schéma). Chacune a un type et une plage, et la page indique si un changement demande un **redémarrage** du moniteur (la boucle lit sa configuration une fois) ou **s'applique tout de suite**.",
           "L'onglet est divisé en sous-onglets, du plus courant au plus avancé : Ce navigateur, Essentiel, Général, Actualisation et limites, Sentinelle, Contrôles de surface (A10), Préparation (A11), Dossiers et fichiers, Sorties, puis les intégrations. Dans un sous-onglet, les réglages sont regroupés en blocs titrés ; le premier champ d'un bloc est son interrupteur principal et, tant qu'il est éteint, le reste du bloc est atténué et non modifiable. Chaque champ affiche son unité (s, min, h, jours, Mo, appels), sa plage, un badge (demande un redémarrage / s'applique tout de suite), un badge pour les options de sécurité qui démarrent à leur valeur prudente et une ligne d'aide. La recherche filtre les réglages de tous les sous-onglets ; chaque sous-onglet compte ses modifications non enregistrées ; les boutons Enregistrer et Annuler restent visibles ; le navigateur retient le dernier sous-onglet. Les onglets suivent le schéma clavier des onglets (flèches, Début, Fin).",
           "Onglet", "Blocs et réglages", "Ce navigateur", "langue de la page, thème (auto / clair / sombre), vue dense de l'onglet Maintenant. Ils restent dans le navigateur, pas dans le fichier.",
           "Un réglage n'apparaît qu'à un seul endroit. Lecture seule : `webhook.signing_state` indique seulement si le secret partagé est défini ; le secret lui-même n'est jamais affiché."),
    "it": ("Cosa si può modificare", "Solo le chiavi dell'elenco di `settings_api.py` (lo schema). Ognuna ha un tipo e un intervallo, e la pagina dice se una modifica richiede il **riavvio** del monitor (il ciclo legge la configurazione una volta) o **si applica subito**.",
           "La scheda è divisa in sotto-schede, dal comune all'avanzato: Questo browser, Di base, Generale, Aggiornamento e limiti, Sentinella, Controlli di superficie (A10), Prontezza (A11), Cartelle e file, Uscite, poi le integrazioni. In ogni sotto-scheda le impostazioni sono in blocchi con titolo; il primo campo di un blocco è il suo interruttore principale e, finché è spento, il resto del blocco è attenuato e non modificabile. Ogni campo mostra l'unità (s, min, h, giorni, MB, chiamate), l'intervallo, un badge (richiede riavvio / si applica subito), un badge per le opzioni di sicurezza che partono dal valore prudente e una riga di aiuto. La ricerca filtra le impostazioni di tutte le sotto-schede; ogni sotto-scheda conta le modifiche non salvate; i pulsanti Salva e Annulla restano visibili; il browser ricorda l'ultima sotto-scheda. Le schede seguono lo schema da tastiera (frecce, Home, Fine).",
           "Scheda", "Blocchi e impostazioni", "Questo browser", "lingua della pagina, tema (auto / chiaro / scuro), vista densa della scheda Adesso. Restano nel browser, non nel file.",
           "Un'impostazione compare in un solo posto. Sola lettura: `webhook.signing_state` dice solo se il segreto condiviso è definito; il segreto non viene mai mostrato."),
    "ja": ("変更できるもの", "`settings_api.py` の一覧(スキーマ)にあるキーだけです。それぞれに型と範囲があり、変更にモニターの**再起動**が必要か(ループは設定を一度だけ読みます)、**すぐ反映**されるかをページが表示します。",
           "このタブは、一般的なものから高度なものの順にサブタブへ分かれています:このブラウザー、基本、一般、更新と上限、センチネル、表面チェック(A10)、準備状況(A11)、フォルダーとファイル、出力、続いて連携。サブタブ内では設定が見出し付きのブロックにまとまり、ブロックの最初の項目がメインのスイッチです。オフの間、ブロックの残りは薄く表示され編集できません。各項目には単位(秒・分・時間・日・MB・回)、範囲、バッジ(再起動が必要/すぐ反映)、保守的な既定値で始まる安全オプションのバッジ、1 行のヘルプが表示されます。検索ボックスは全サブタブの設定を絞り込み、各サブタブは未保存の変更数を数え、保存と破棄のボタンは常に見え、最後に使ったサブタブはブラウザーが覚えます。タブはキーボード操作(矢印キー、Home、End)に対応します。",
           "タブ", "ブロックと設定", "このブラウザー", "ページの言語、テーマ(自動/ライト/ダーク)、「今」タブの高密度表示。ファイルではなくブラウザーに保存されます。",
           "各設定は 1 か所にだけ現れます。読み取り専用:`webhook.signing_state` は共有シークレットが設定済みかどうかだけを示し、シークレット自体は表示されません。"),
    "zh": ("可以更改的内容", "只有 `settings_api.py` 列表(架构)中的键。每个键都有类型和范围,页面会说明更改是需要**重启**监视器(循环只读取一次配置)还是**立即生效**。",
           "该标签页按从常用到高级的顺序分为子标签页:此浏览器、基本、常规、刷新与限制、哨兵、表面检查(A10)、就绪(A11)、文件夹与文件、输出,然后是集成。每个子标签页内的设置按带标题的块分组;块的第一个字段是它的总开关,关闭时该块其余部分变暗且不可编辑。每个字段都显示单位(秒、分钟、小时、天、MB、次)、范围、徽标(需要重启/立即生效)、以保守默认值启动的安全选项徽标,以及一行帮助。搜索框会筛选所有子标签页的设置;每个子标签页统计未保存的更改;保存和放弃按钮始终可见;浏览器会记住上次使用的子标签页。标签页遵循键盘操作模式(方向键、Home、End)。",
           "标签页", "块与设置", "此浏览器", "页面语言、主题(自动/浅色/深色)、“现在”标签页的紧凑视图。它们保存在浏览器中,而不是文件中。",
           "每项设置只出现在一个地方。只读:`webhook.signing_state` 仅说明共享密钥是否已定义;密钥本身永不显示。"),
    "pt": ("O que se pode alterar", "Apenas as chaves da lista de `settings_api.py` (o esquema). Cada uma tem um tipo e um intervalo, e a página diz se uma alteração precisa de **reiniciar** o monitor (o ciclo lê a configuração uma vez) ou **aplica-se já**.",
           "O separador divide-se em subseparadores, ordenados do comum ao avançado: Este navegador, Básico, Geral, Atualização e limites, Sentinela, Verificações de superfície (A10), Prontidão (A11), Pastas e ficheiros, Saídas e depois as integrações. Dentro de cada subseparador as definições estão em blocos com título; o primeiro campo de um bloco é o seu interruptor principal e, enquanto estiver desligado, o resto do bloco fica esbatido e não se pode editar. Cada campo mostra a unidade (s, min, h, dias, MB, chamadas), o intervalo, um distintivo (pede reinício / aplica-se já), outro para as opções de segurança que arrancam no estado conservador e uma linha de ajuda. A pesquisa filtra as definições de todos os subseparadores; cada subseparador conta as alterações por guardar; os botões Guardar e Descartar estão sempre visíveis; o navegador lembra o último subseparador. Os separadores seguem o padrão de teclado dos separadores (setas, Início, Fim).",
           "Separador", "Blocos e definições", "Este navegador", "idioma da página, tema (auto / claro / escuro), vista densa do separador Agora. Ficam no navegador, não no ficheiro.",
           "Cada definição aparece num só sítio. Só de leitura: `webhook.signing_state` apenas diz se o segredo partilhado está definido; o segredo nunca é mostrado."),
}


PINS_EXAMPLE = """```jsonc
// Example, commented out: where the pinned versions of an ecosystem live. Copy the part you need into
// "sentinel" > "readiness" > "pins" > "sources" of actions_monitor.json (or paste it in the Settings tab) and remove the comments.
// [
//   {"ecosystem": "alpha", "kind": "pin_table", "provider": "ALPHA-COMMON", "file": "pins/consumers.json", "key": "consumers"},
//   {"ecosystem": "beta",  "kind": "lock_files", "provider": "BETA-CORE", "lock_name": "beta.lock.json", "version_key": "core"}
// ]
// pin_table: a JSON file of the provider that maps each repository to the version it pins (under "key").
// lock_files: every clone is searched (down to "max_depth" folder levels) for files called "lock_name"; the OLDEST version found in "version_key" counts.
```"""
PINS = {
    "en": ("Example of pin sources", "The pins are read only when a source is listed; with an empty list nothing is read and the page says so. The text below is an example, commented out:"),
    "es": ("Ejemplo de fuentes de versiones fijadas", "Las versiones fijadas solo se leen si hay una fuente; con la lista vacía no se lee nada y la página lo dice. El texto siguiente es un ejemplo, comentado:"),
    "de": ("Beispiel für Quellen der Fixierungen", "Die Fixierungen werden nur gelesen, wenn eine Quelle eingetragen ist; bei leerer Liste wird nichts gelesen, und die Seite sagt es. Der folgende Text ist ein auskommentiertes Beispiel:"),
    "fr": ("Exemple de sources d'épinglage", "Les versions épinglées ne sont lues que si une source est indiquée ; avec une liste vide rien n'est lu et la page le dit. Le texte suivant est un exemple, commenté :"),
    "it": ("Esempio di fonti delle versioni fissate", "Le versioni fissate si leggono solo se è indicata una fonte; con l'elenco vuoto non si legge nulla e la pagina lo dice. Il testo seguente è un esempio, commentato:"),
    "ja": ("固定バージョンの取得元の例", "固定バージョンは取得元を指定したときだけ読み取られます。リストが空なら何も読まず、ページがそう表示します。次はコメントアウトした例です:"),
    "zh": ("固定版本来源示例", "只有列出了来源才会读取固定版本;列表为空时不读取任何内容,页面会如实说明。下面是一个已注释的示例:"),
    "pt": ("Exemplo de fontes de versões fixadas", "As versões fixadas só são lidas se houver uma fonte; com a lista vazia nada é lido e a página di-lo. O texto seguinte é um exemplo, comentado:"),
}


AI_NOTE = {
    "en": "External AI: `ai.provider` can be `ollama` (this computer), `openai-compatible` (any OpenAI-style endpoint, which also serves Gemini through its OpenAI-compatible endpoint and OpenAI itself), `anthropic` (the Messages API; you choose the model) or `copilot` (`gh copilot` with your own login; it spends premium requests). The key is never saved: only the NAME of the environment variable. See AI.md.",
    "es": "IA externa: `ai.provider` puede ser `ollama` (este equipo), `openai-compatible` (cualquier endpoint estilo OpenAI, que sirve también para Gemini mediante su endpoint compatible con OpenAI y para OpenAI), `anthropic` (la API Messages; el modelo lo eliges tú) o `copilot` (`gh copilot` con tu propio acceso; gasta solicitudes premium). La clave nunca se guarda: solo el NOMBRE de la variable de entorno. Ver AI_spa.md.",
    "de": "Externe KI: `ai.provider` kann `ollama` (dieser Rechner), `openai-compatible` (jeder Endpunkt im OpenAI-Stil, der auch Gemini über dessen OpenAI-kompatiblen Endpunkt und OpenAI selbst bedient), `anthropic` (die Messages-API; das Modell wählen Sie) oder `copilot` (`gh copilot` mit Ihrem Login; verbraucht Premium-Anfragen) sein. Der Schlüssel wird nie gespeichert: nur der NAME der Umgebungsvariable. Siehe AI_deu.md.",
    "fr": "IA externe : `ai.provider` peut valoir `ollama` (cet ordinateur), `openai-compatible` (tout point d'accès de style OpenAI, qui sert aussi pour Gemini via son point d'accès compatible OpenAI et pour OpenAI), `anthropic` (l'API Messages ; vous choisissez le modèle) ou `copilot` (`gh copilot` avec votre connexion ; consomme des requêtes premium). La clé n'est jamais enregistrée : seulement le NOM de la variable d'environnement. Voir AI_fra.md.",
    "it": "IA esterna: `ai.provider` può essere `ollama` (questo computer), `openai-compatible` (qualsiasi endpoint in stile OpenAI, che serve anche per Gemini tramite il suo endpoint compatibile OpenAI e per OpenAI), `anthropic` (l'API Messages; il modello lo scegli tu) o `copilot` (`gh copilot` con il tuo accesso; consuma richieste premium). La chiave non viene mai salvata: solo il NOME della variabile d'ambiente. Vedi AI_ita.md.",
    "ja": "外部 AI:`ai.provider` は `ollama`(このコンピューター)、`openai-compatible`(OpenAI 形式の任意のエンドポイント。Gemini の OpenAI 互換エンドポイントや OpenAI 自体にも使えます)、`anthropic`(Messages API。モデルは自分で選びます)、`copilot`(自分のログインで `gh copilot` を実行。プレミアムリクエストを消費)のいずれかです。キーは保存されず、環境変数の名前だけを設定します。AI_jpn.md を参照。",
    "zh": "外部 AI:`ai.provider` 可以是 `ollama`(本机)、`openai-compatible`(任何 OpenAI 风格的端点,也适用于 Gemini 的 OpenAI 兼容端点和 OpenAI 本身)、`anthropic`(Messages API;模型由你选择)或 `copilot`(用你自己的登录运行 `gh copilot`;会消耗高级请求)。密钥从不保存:只设置环境变量的名称。见 AI_zho.md。",
    "pt": "IA externa: `ai.provider` pode ser `ollama` (este computador), `openai-compatible` (qualquer endpoint ao estilo OpenAI, que serve também para o Gemini através do seu endpoint compatível com OpenAI e para a OpenAI), `anthropic` (a API Messages; o modelo é você que o escolhe) ou `copilot` (`gh copilot` com o seu acesso; gasta pedidos premium). A chave nunca é guardada: só o NOME da variável de ambiente. Ver AI_por.md.",
}


ECO_NEW = {'en': 'Which repositories are watched: the example catalogue of ecosystems ends with a group `rest` (prefix `*`, "Everything else") that takes every repository no other group claims, so nothing is left out by default. If your own catalogue leaves repositories out, a banner of the page says how many ("your ecosystem filter hides N of the M repositories of the account").', 'es': 'Qué repositorios se vigilan: el catálogo de ejemplo de ecosistemas termina con un grupo `rest` (prefijo `*`, «Everything else») que recoge todo repositorio que ningún otro grupo reclama, así que por defecto no queda nada fuera. Si tu propio catálogo deja repositorios fuera, un aviso de la página dice cuántos («tu filtro de ecosistemas oculta N de los M repositorios de la cuenta»).', 'de': 'Welche Repositorys beobachtet werden: Der Beispielkatalog der Ökosysteme endet mit einer Gruppe `rest` (Präfix `*`, „Everything else“), die jedes Repository aufnimmt, das keine andere Gruppe beansprucht; so bleibt standardmäßig nichts außen vor. Lässt Ihr eigener Katalog Repositorys aus, nennt ein Banner der Seite die Anzahl („Ihr Ökosystem-Filter blendet N von M Repositorys des Kontos aus“).', 'fr': "Quels dépôts sont surveillés : le catalogue d'exemple des écosystèmes se termine par un groupe `rest` (préfixe `*`, « Everything else ») qui prend tout dépôt qu'aucun autre groupe ne réclame, donc rien n'est laissé de côté par défaut. Si votre propre catalogue en laisse, un bandeau de la page dit combien (« votre filtre d'écosystèmes masque N des M dépôts du compte »).", 'it': "Quali repository si osservano: il catalogo di esempio degli ecosistemi termina con un gruppo `rest` (prefisso `*`, «Everything else») che prende ogni repository che nessun altro gruppo rivendica, quindi per impostazione predefinita nulla resta fuori. Se il tuo catalogo ne lascia fuori, un avviso della pagina dice quanti («il tuo filtro degli ecosistemi nasconde N dei M repository dell'account»).", 'ja': 'どのリポジトリを監視するか:エコシステムのサンプルカタログは、他のどのグループにも属さないリポジトリをすべて受け取るグループ `rest`(接頭辞 `*`、「Everything else」)で終わるため、既定では何も漏れません。自分のカタログで漏れるリポジトリがある場合は、ページのバナーがその数を表示します(「エコシステムのフィルターがアカウントの M 件中 N 件を隠しています」)。', 'zh': '监视哪些仓库:生态系统示例目录以一个 `rest` 组(前缀 `*`,“Everything else”)结尾,它接收其他组都不认领的所有仓库,因此默认不会遗漏任何仓库。如果你自己的目录遗漏了仓库,页面横幅会告诉你数量(“你的生态系统筛选器隐藏了账户 M 个仓库中的 N 个”)。', 'pt': 'Que repositórios são vigiados: o catálogo de exemplo de ecossistemas termina com um grupo `rest` (prefixo `*`, «Everything else») que recolhe todo o repositório que nenhum outro grupo reclama, por isso por predefinição nada fica de fora. Se o seu próprio catálogo deixar repositórios de fora, um aviso da página diz quantos («o seu filtro de ecossistemas oculta N dos M repositórios da conta»).'}


def locale(lang):
    return json.loads((MON / "assets" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))


def render(lang):
    cat = locale(lang)
    heading, intro, structure, col_tab, col_blocks, browser_name, browser_text, tail = TEXT[lang]
    lines = [BEGIN, f"## {heading}", "", intro, "", structure, "", f"| {col_tab} | {col_blocks} |", "|---|---|", f"| {browser_name} | {browser_text} |"]
    for tab, blocks in sa.layout():
        cells = []
        for block, keys in blocks:
            title = cat[sa.block_title_key(block)]
            if block.startswith("chk_"):
                names = ", ".join(f"`{k.rsplit('.', 1)[1]}`" for k in keys)
                cells.append(f"**{title}**: `sentinel.surface.checks.{block[4:]}.*` ({names})")
            else:
                cells.append(f"**{title}**: " + ", ".join(f"`{k}`" for k in keys))
        lines.append(f"| {cat['ui.cfg_g_' + tab]} | " + "<br>".join(cells) + " |")
    lines += ["", tail, "", ECO_NEW[lang], "", AI_NOTE[lang], "", f"### {PINS[lang][0]}", "", PINS[lang][1], "", PINS_EXAMPLE, END]
    return "\n".join(lines)


def patched(text, block):
    if BEGIN in text and END in text:
        a, b = text.index(BEGIN), text.index(END) + len(END)
        return text[:a] + block + text[b:]
    # first run: replace the first "## " section (the old list of groups) and wrap the new one in markers
    a = text.index("\n## ") + 1
    b = text.index("\n## ", a + 3) + 1
    return text[:a] + block + "\n\n" + text[b:]


def main():
    check = "--check" in sys.argv
    bad = 0
    for lang, name in FILES.items():
        path = MON / "docs" / name
        old = path.read_text(encoding="utf-8")
        new = patched(old, render(lang))
        if new != old:
            if check:
                print("out of date:", name)
                bad += 1
            else:
                path.write_text(new, encoding="utf-8", newline="\n")
                print("written", name)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
