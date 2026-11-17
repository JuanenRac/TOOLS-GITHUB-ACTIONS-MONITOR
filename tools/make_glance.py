#!/usr/bin/env python3
# =============================================================================
# GitHub Actions Monitor - tools/make_glance.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D)
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The facts of the README ("At a glance" extra rows) and the table "Project status" with its lights, written from the repository itself, in the eight languages.

    python tools/make_glance.py            write the block in README.md and its seven translations
    python tools/make_glance.py --check    fail when a README differs from what the repository gives (the CI runs it)

The block lives between `<!-- glance:begin -->` and `<!-- glance:end -->`. What is measured, never typed: the version (monitor/src/github_actions_monitor/tool_version.py), the number of tests (the test methods of
monitor/tests, counted from the source), the number of settings (the schema of the Settings page), the languages, the systems and Python versions of the CI (.github/workflows/ci.yml) and
the maturity (the project manifest). The lights follow the rule of the ecosystem: only the light in the State column; nothing is green that has not run in the real environment.
"""
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MON = ROOT / "monitor"
sys.path.insert(0, str(MON / "src"))
SUFFIX = {"en": "", "es": "_spa", "fr": "_fra", "it": "_ita", "de": "_deu", "zh": "_zho", "ja": "_jpn", "pt": "_por"}
BEGIN, END = "<!-- glance:begin -->", "<!-- glance:end -->"


def facts():
    version = re.search(r'TOOL_VERSION\s*=\s*"([^"]+)"', (MON / "src" / "github_actions_monitor" / "tool_version.py").read_text(encoding="utf-8")).group(1)
    tests = 0      # every `test*` method of every class of the test files (a class that inherits from a base of its own counts as well); the run prints a higher number because each subclass runs the methods it inherits too
    for path in sorted((MON / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                tests += sum(1 for f in node.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name.startswith("test"))
    from github_actions_monitor.app import settings_api
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    systems = re.search(r"os:\s*\[([^\]]+)\]", ci).group(1)
    pythons = re.search(r"python:\s*\[([^\]]+)\]", ci).group(1)
    manifest = json.loads((ROOT / "electro-hobby-3d.project.json").read_text(encoding="utf-8"))
    return {"version": version, "tests": tests, "settings": len(settings_api.FIELDS), "systems": ", ".join(s.strip().replace("-latest", "").strip() for s in systems.split(",")),
            "pythons": ", ".join(p.strip().strip('"') for p in pythons.split(",")), "maturity": manifest.get("maturity", "functional")}


# label of each row, per language: tests, settings, languages, CI, maturity
L = {
    "en": dict(h="Measured today", k=("Maturity", "Tests", "Settings", "Languages", "Tested in the CI on"), tests="{n} test methods (`python -m unittest discover -s monitor/tests`)", sets="{n} settings, all with help", langs="8 (English, Spanish, German, French, Italian, Japanese, Chinese, Portuguese)", ci="{s}, Python {p}",
               ps="Project status", intro="Each line is one part of this repository and the light says how far it is today: what the tests and the CI can show and what has run for real, not what is planned.", legend="🟢 Done and verified · 🟡 Works, with known limits · 🟠 Partly done or not verified yet · 🔴 Not done or not working", cols=("Area", "State", "What it means here")),
    "es": dict(h="Medido hoy", k=("Madurez", "Tests", "Ajustes", "Idiomas", "Probado en el CI en"), tests="{n} métodos de test (`python -m unittest discover -s monitor/tests`)", sets="{n} ajustes, todos con ayuda", langs="8 (inglés, español, alemán, francés, italiano, japonés, chino y portugués)", ci="{s}, Python {p}",
               ps="Estado del proyecto", intro="Cada línea es una parte de este repositorio y la luz dice hasta dónde llega hoy: lo que pueden mostrar los tests y el CI y lo que se ha ejecutado de verdad, no lo planeado.", legend="🟢 Hecho y verificado · 🟡 Funciona, con límites conocidos · 🟠 Hecho en parte o sin verificar todavía · 🔴 Sin hacer o sin funcionar", cols=("Área", "Estado", "Qué significa aquí")),
    "fr": dict(h="Mesuré aujourd'hui", k=("Maturité", "Tests", "Réglages", "Langues", "Testé dans le CI sur"), tests="{n} méthodes de test (`python -m unittest discover -s monitor/tests`)", sets="{n} réglages, tous avec aide", langs="8 (anglais, espagnol, allemand, français, italien, japonais, chinois et portugais)", ci="{s}, Python {p}",
               ps="État du projet", intro="Chaque ligne est une partie de ce dépôt et le voyant dit où elle en est aujourd'hui : ce que les tests et le CI peuvent montrer et ce qui a tourné pour de vrai, pas ce qui est prévu.", legend="🟢 Fait et vérifié · 🟡 Fonctionne, avec des limites connues · 🟠 En partie fait ou pas encore vérifié · 🔴 Pas fait ou ne fonctionne pas", cols=("Domaine", "État", "Ce que cela veut dire ici")),
    "it": dict(h="Misurato oggi", k=("Maturità", "Test", "Impostazioni", "Lingue", "Provato nel CI su"), tests="{n} metodi di test (`python -m unittest discover -s monitor/tests`)", sets="{n} impostazioni, tutte con aiuto", langs="8 (inglese, spagnolo, tedesco, francese, italiano, giapponese, cinese e portoghese)", ci="{s}, Python {p}",
               ps="Stato del progetto", intro="Ogni riga è una parte di questo repository e il semaforo dice a che punto è oggi: ciò che i test e il CI possono mostrare e ciò che è girato davvero, non ciò che è previsto.", legend="🟢 Fatto e verificato · 🟡 Funziona, con limiti noti · 🟠 In parte fatto o non ancora verificato · 🔴 Non fatto o non funzionante", cols=("Area", "Stato", "Cosa significa qui")),
    "de": dict(h="Heute gemessen", k=("Reifegrad", "Tests", "Einstellungen", "Sprachen", "Im CI getestet auf"), tests="{n} Testmethoden (`python -m unittest discover -s monitor/tests`)", sets="{n} Einstellungen, alle mit Hilfe", langs="8 (Englisch, Spanisch, Deutsch, Französisch, Italienisch, Japanisch, Chinesisch und Portugiesisch)", ci="{s}, Python {p}",
               ps="Projektstatus", intro="Jede Zeile ist ein Teil dieses Repositories, und die Ampel sagt, wie weit er heute ist: was die Tests und das CI zeigen können und was wirklich gelaufen ist, nicht was geplant ist.", legend="🟢 Fertig und geprüft · 🟡 Funktioniert, mit bekannten Grenzen · 🟠 Teilweise fertig oder noch nicht geprüft · 🔴 Nicht fertig oder funktioniert nicht", cols=("Bereich", "Stand", "Was das hier bedeutet")),
    "zh": dict(h="今日实测", k=("成熟度", "测试", "设置", "语言", "CI 测试平台"), tests="{n} 个测试方法(`python -m unittest discover -s monitor/tests`)", sets="{n} 个设置,均有帮助", langs="8 种(英语、西班牙语、德语、法语、意大利语、日语、中文和葡萄牙语)", ci="{s},Python {p}",
               ps="项目状态", intro="每一行是本仓库的一个部分,指示灯表示它今天的进度:测试和 CI 能证明的、以及真正运行过的,而不是计划中的。", legend="🟢 已完成并验证 · 🟡 可用,有已知限制 · 🟠 部分完成或尚未验证 · 🔴 未完成或不能用", cols=("范围", "状态", "含义")),
    "ja": dict(h="現時点の実測", k=("成熟度", "テスト", "設定", "言語", "CI で検証したシステム"), tests="テストメソッド {n} 件(`python -m unittest discover -s monitor/tests`)", sets="設定 {n} 件、すべてヘルプ付き", langs="8(英語、スペイン語、ドイツ語、フランス語、イタリア語、日本語、中国語、ポルトガル語)", ci="{s}、Python {p}",
               ps="プロジェクトの状況", intro="各行はこのリポジトリの一部分で、信号は現時点の到達度を示します。テストと CI が示せること、実際に動いたことであり、予定ではありません。", legend="🟢 完了・検証済み · 🟡 動作するが既知の制限あり · 🟠 一部のみ、または未検証 · 🔴 未完了または動作せず", cols=("領域", "状態", "ここでの意味")),
    "pt": dict(h="Medido hoje", k=("Maturidade", "Testes", "Definições", "Idiomas", "Testado no CI em"), tests="{n} métodos de teste (`python -m unittest discover -s monitor/tests`)", sets="{n} definições, todas com ajuda", langs="8 (inglês, espanhol, alemão, francês, italiano, japonês, chinês e português)", ci="{s}, Python {p}",
               ps="Estado do projeto", intro="Cada linha é uma parte deste repositório e a luz diz até onde chega hoje: o que os testes e o CI podem mostrar e o que correu de verdade, não o que está planeado.", legend="🟢 Feito e verificado · 🟡 Funciona, com limites conhecidos · 🟠 Feito em parte ou ainda não verificado · 🔴 Por fazer ou a não funcionar", cols=("Área", "Estado", "O que significa aqui")),
}
# the rows of the status table: (light, text per language). The lights are written by hand on purpose: they are a judgement about what has run for real.
ROWS = [
    ("🟢", {"en": ("Monitor and page", "Runs every day on a real account; the tests run in the CI on Ubuntu and Windows."), "es": ("Monitor y página", "Funciona cada día con una cuenta real; los tests corren en el CI en Ubuntu y Windows."),
            "fr": ("Moniteur et page", "Tourne chaque jour sur un vrai compte ; les tests tournent dans le CI sous Ubuntu et Windows."), "it": ("Monitor e pagina", "Gira ogni giorno su un account reale; i test girano nel CI su Ubuntu e Windows."),
            "de": ("Monitor und Seite", "Läuft täglich mit einem echten Konto; die Tests laufen im CI auf Ubuntu und Windows."), "zh": ("监视器与页面", "每天在真实账户上运行;测试在 CI 的 Ubuntu 和 Windows 上运行。"),
            "ja": ("モニターとページ", "実際のアカウントで毎日動作。テストは CI の Ubuntu と Windows で実行。"), "pt": ("Monitor e página", "Corre todos os dias numa conta real; os testes correm no CI em Ubuntu e Windows.")}),
    ("🟢", {"en": ("Sentinel (A1..A13)", "Runs every day on a real account; its levels and rows are tested with fixtures."), "es": ("Centinela (A1..A13)", "Funciona cada día con una cuenta real; sus niveles y filas se prueban con fixtures."),
            "fr": ("Sentinelle (A1..A13)", "Tourne chaque jour sur un vrai compte ; ses niveaux et lignes sont testés avec des fixtures."), "it": ("Sentinella (A1..A13)", "Gira ogni giorno su un account reale; livelli e righe sono testati con fixture."),
            "de": ("Sentinel (A1..A13)", "Läuft täglich mit einem echten Konto; Stufen und Zeilen werden mit Fixtures getestet."), "zh": ("哨兵(A1..A13)", "每天在真实账户上运行;其级别和行用固定数据测试。"),
            "ja": ("センチネル(A1..A13)", "実際のアカウントで毎日動作。レベルと行はフィクスチャーでテスト。"), "pt": ("Sentinela (A1..A13)", "Corre todos os dias numa conta real; os níveis e linhas são testados com fixtures.")}),
    ("🟡", {"en": ("Notifications", "Tested against simulated servers; not every channel has been tried against the real service."), "es": ("Notificaciones", "Probadas contra servidores simulados; no todos los canales se han probado con el servicio real."),
            "fr": ("Notifications", "Testées contre des serveurs simulés ; tous les canaux n'ont pas été essayés avec le vrai service."), "it": ("Notifiche", "Provate contro server simulati; non tutti i canali sono stati provati con il servizio reale."),
            "de": ("Benachrichtigungen", "Gegen simulierte Server getestet; nicht jeder Kanal wurde am echten Dienst probiert."), "zh": ("通知", "已针对模拟服务器测试;并非每个渠道都在真实服务上试过。"),
            "ja": ("通知", "模擬サーバーでテスト済み。すべてのチャネルを実サービスで試したわけではありません。"), "pt": ("Notificações", "Testadas contra servidores simulados; nem todos os canais foram experimentados com o serviço real.")}),
    ("🟡", {"en": ("Connection with an AI tool and MCP", "The feed, the state, the stream, the hook and the MCP tools are tested with a real server and a simulated client; no independent user has run them yet."), "es": ("Conexión con una IA y MCP", "El flujo, el estado, el flujo en directo, el hook y las herramientas MCP se prueban con un servidor real y un cliente simulado; ningún usuario independiente los ha usado todavía."),
            "fr": ("Connexion à un outil d'IA et MCP", "Le flux, l'état, le flux en direct, le hook et les outils MCP sont testés avec un vrai serveur et un client simulé ; aucun utilisateur indépendant ne les a encore utilisés."), "it": ("Connessione a uno strumento di IA e MCP", "Feed, stato, flusso, hook e strumenti MCP sono testati con un server reale e un client simulato; nessun utente indipendente li ha ancora usati."),
            "de": ("Verbindung zu einem KI-Werkzeug und MCP", "Feed, Zustand, Stream, Hook und MCP-Werkzeuge sind mit einem echten Server und einem simulierten Client getestet; noch kein unabhängiger Nutzer hat sie benutzt."), "zh": ("AI 工具连接与 MCP", "信息流、状态、事件流、钩子和 MCP 工具已用真实服务器和模拟客户端测试;尚无独立用户使用过。"),
            "ja": ("AI ツール接続と MCP", "フィード、状態、ストリーム、フック、MCP ツールは実サーバーと模擬クライアントでテスト済み。独立したユーザーはまだ使っていません。"), "pt": ("Ligação a uma ferramenta de IA e MCP", "O feed, o estado, o fluxo, o hook e as ferramentas MCP são testados com um servidor real e um cliente simulado; nenhum utilizador independente os usou ainda.")}),
    ("🟡", {"en": ("Lite edition", "Tested in the CI and shares the channels and settings of the complete one; little real use so far."), "es": ("Edición lite", "Probada en el CI y comparte los canales y ajustes de la completa; poco uso real hasta ahora."),
            "fr": ("Édition lite", "Testée dans le CI et partage les canaux et réglages de la complète ; peu d'usage réel jusqu'ici."), "it": ("Edizione lite", "Provata nel CI e condivide canali e impostazioni di quella completa; finora poco uso reale."),
            "de": ("Lite-Edition", "Im CI getestet und teilt Kanäle und Einstellungen mit der vollständigen; bisher wenig echter Einsatz."), "zh": ("Lite 版", "已在 CI 中测试,与完整版共用通道和设置;迄今实际使用较少。"),
            "ja": ("Lite 版", "CI でテスト済みで、完全版とチャネルと設定を共有。実使用はこれまで少なめ。"), "pt": ("Edição lite", "Testada no CI e partilha os canais e definições da completa; pouco uso real até agora.")}),
    ("🟠", {"en": ("GitHub App, central panel and Low mode", "New: tested with simulated servers and files; not yet run for a long time against the real service."), "es": ("GitHub App, panel central y modo Bajo", "Nuevo: probado con servidores y ficheros simulados; todavía no ha funcionado mucho tiempo con el servicio real."),
            "fr": ("GitHub App, panneau central et mode économe", "Nouveau : testé avec des serveurs et fichiers simulés ; pas encore tourné longtemps avec le vrai service."), "it": ("GitHub App, pannello centrale e modalità risparmio", "Novità: provato con server e file simulati; non ha ancora girato a lungo con il servizio reale."),
            "de": ("GitHub-App, zentrales Panel und Sparmodus", "Neu: mit simulierten Servern und Dateien getestet; noch nicht lange gegen den echten Dienst gelaufen."), "zh": ("GitHub App、中央面板和节省模式", "新功能:已用模拟服务器和文件测试;尚未长时间对真实服务运行。"),
            "ja": ("GitHub App、中央パネル、節約モード", "新機能:模擬サーバーとファイルでテスト済み。実サービスでの長期稼働はまだありません。"), "pt": ("GitHub App, painel central e modo poupança", "Novo: testado com servidores e ficheiros simulados; ainda não correu muito tempo com o serviço real.")}),
    ("🟡", {"en": ('Score of each account', 'Tested with synthetic series, fixtures and simulated servers; it has not been watched for weeks on real accounts yet.'), "es": ('Puntuación de cada cuenta', 'Probada con series sintéticas, datos de prueba y servidores simulados; todavía no se ha vigilado durante semanas en cuentas reales.'), "fr": ('Score de chaque compte', "Testé avec des séries synthétiques, des jeux d'essai et des serveurs simulés ; il n'a pas encore été observé pendant des semaines sur de vrais comptes."), "it": ('Punteggio di ogni account', 'Provato con serie sintetiche, dati di prova e server simulati; non è ancora stato osservato per settimane su account reali.'), "de": ('Punktzahl jedes Kontos', 'Mit synthetischen Reihen, Testdaten und simulierten Servern geprüft; noch nicht wochenlang an echten Konten beobachtet.'), "zh": ('每个账户的评分', '已用合成数据序列、测试数据和模拟服务器验证；尚未在真实账户上连续观察数周。'), "ja": ('アカウントごとのスコア', '合成データ、テスト用データ、模擬サーバーで検証済み。実アカウントで数週間見守った実績はまだありません。'), "pt": ('Pontuação de cada conta', 'Testada com séries sintéticas, dados de teste e servidores simulados; ainda não foi observada durante semanas em contas reais.')}),
    ("🟡", {"en": ('Docker image and service mode', 'The image is built and tested in the CI (non-root, read-only, a revoked login); little time yet as a long-lived service.'), "es": ('Imagen de Docker y modo servicio', 'La imagen se construye y se prueba en la CI (sin root, de solo lectura, con un acceso revocado); aún poco tiempo como servicio de larga duración.'), "fr": ('Image Docker et mode service', "L'image est construite et testée dans la CI (sans root, en lecture seule, avec une connexion révoquée) ; encore peu de temps comme service de longue durée."), "it": ('Immagine Docker e modalità servizio', "L'immagine è costruita e provata nella CI (senza root, in sola lettura, con un accesso revocato); ancora poco tempo come servizio di lunga durata."), "de": ('Docker-Image und Dienstmodus', 'Das Image wird in der CI gebaut und geprüft (ohne Root, schreibgeschützt, mit widerrufener Anmeldung); noch wenig Zeit als Langzeitdienst.'), "zh": ('Docker 镜像与服务模式', '镜像在 CI 中构建并验证（非 root、只读、登录被撤销）；作为长期运行服务的时间还不长。'), "ja": ('Docker イメージとサービスモード', 'イメージは CI でビルドして検証済み（非 root、読み取り専用、失効したログイン）。長期稼働のサービスとしての実績はまだ短いです。'), "pt": ('Imagem Docker e modo de serviço', 'A imagem é construída e testada na CI (sem root, só de leitura, com um acesso revogado); ainda pouco tempo como serviço de longa duração.')}),
    ("🟡", {"en": ('Team mode and several accounts', 'Tested with real processes and simulated users; a real team has not used it for long.'), "es": ('Modo equipo y varias cuentas', 'Probado con procesos reales y usuarios simulados; un equipo real no lo ha usado durante mucho tiempo.'), "fr": ('Mode équipe et plusieurs comptes', "Testé avec de vrais processus et des utilisateurs simulés ; une vraie équipe ne l'a pas utilisé longtemps."), "it": ('Modalità squadra e più account', "Provata con processi reali e utenti simulati; un vero team non l'ha usata a lungo."), "de": ('Teammodus und mehrere Konten', 'Mit echten Prozessen und simulierten Benutzern geprüft; ein echtes Team hat ihn noch nicht lange genutzt.'), "zh": ('团队模式与多账户', '已用真实进程和模拟用户验证；真实团队尚未长期使用。'), "ja": ('チームモードと複数アカウント', '実プロセスと模擬ユーザーで検証済み。実際のチームが長く使った実績はまだありません。'), "pt": ('Modo de equipa e várias contas', 'Testado com processos reais e utilizadores simulados; uma equipa real ainda não o usou durante muito tempo.')}),
    ("🟡", {"en": ('Storage (files and SQLite)', 'Tested with both backends and the migrations between them; a database that is months old has not been through an upgrade yet.'), "es": ('Almacenamiento (ficheros y SQLite)', 'Probado con los dos soportes y las migraciones entre ellos; una base de datos de meses todavía no ha pasado por una actualización.'), "fr": ('Stockage (fichiers et SQLite)', "Testé avec les deux supports et les migrations entre eux ; une base de données de plusieurs mois n'a pas encore connu de mise à jour."), "it": ('Archiviazione (file e SQLite)', 'Provata con i due archivi e le migrazioni tra loro; un database vecchio di mesi non ha ancora attraversato un aggiornamento.'), "de": ('Speicherung (Dateien und SQLite)', 'Mit beiden Speichern und den Migrationen dazwischen geprüft; eine monatealte Datenbank hat noch kein Update durchlaufen.'), "zh": ('存储（文件与 SQLite）', '已用两种存储及其间的迁移验证；已使用数月的数据库尚未经历过升级。'), "ja": ('ストレージ（ファイルと SQLite）', '両方のバックエンドと、その間の移行で検証済み。数か月経ったデータベースのアップグレードはまだ経験していません。'), "pt": ('Armazenamento (ficheiros e SQLite)', 'Testado com os dois suportes e as migrações entre eles; uma base de dados com meses ainda não passou por uma atualização.')}),
    ("🟠", {"en": ("Linux and macOS", "Linux is tested in the CI only; macOS is not tested in the CI for now; the daily use is on Windows."), "es": ("Linux y macOS", "Linux se prueba solo en el CI; macOS no se prueba en el CI por ahora; el uso diario es en Windows."), "fr": ("Linux et macOS", "Linux n'est testé que dans le CI ; macOS n'est pas testé dans le CI pour l'instant ; l'usage quotidien est sous Windows."),
            "it": ("Linux e macOS", "Linux è provato solo nel CI; macOS per ora non è provato nel CI; l'uso quotidiano è su Windows."), "de": ("Linux und macOS", "Linux wird nur im CI getestet; macOS wird vorerst nicht im CI getestet; der tägliche Einsatz ist unter Windows."), "zh": ("Linux 和 macOS", "Linux 仅在 CI 中测试;macOS 暂不在 CI 中测试;日常使用在 Windows 上。"),
            "ja": ("Linux と macOS", "Linux は CI でのみテスト。macOS は当面 CI ではテストしません。日常の使用は Windows です。"), "pt": ("Linux e macOS", "O Linux é testado só no CI; o macOS não é testado no CI por agora; o uso diário é no Windows.")}),
]


def block(lang, f):
    t = L[lang]
    rows = [f"| **{t['k'][0]}** | {f['maturity']} |", f"| **{t['k'][1]}** | {t['tests'].format(n=f['tests'])} |", f"| **{t['k'][2]}** | {t['sets'].format(n=f['settings'])} |",
            f"| **{t['k'][3]}** | {t['langs']} |", f"| **{t['k'][4]}** | {t['ci'].format(s=f['systems'], p=f['pythons'])} |"]
    status = "\n".join(f"| {r[1][lang][0]} | {r[0]} | {r[1][lang][1]} |" for r in ROWS)
    return (f"{BEGIN}\n\n**{t['h']}** (v{f['version']})\n\n| | |\n|---|---|\n" + "\n".join(rows) + f"\n\n## {t['ps']}\n\n{t['intro']}\n\n{t['legend']}\n\n| {t['cols'][0]} | {t['cols'][1]} | {t['cols'][2]} |\n|---|---|---|\n{status}\n\n{END}")


BADGE_RE = re.compile(r'<img src="https://img\.shields\.io/badge/Tests-[\d,.]+_passing-brightgreen\.svg" alt="[^"]*">')
LANGUAGES_BADGE_RE = re.compile(r'^([ \t]*)<img src="https://img\.shields\.io/badge/Languages-8-[^\n]*\n', re.M)


def tests_badge(f):
    """The badge with the number of tests (the dashboard of the profile reads `Tests-<number>` in the README): the same count as the table, measured and never typed."""
    return f'<img src="https://img.shields.io/badge/Tests-{f["tests"]}_passing-brightgreen.svg" alt="{f["tests"]} tests">'


def with_badge(text, f):
    if BADGE_RE.search(text):
        return BADGE_RE.sub(lambda m: tests_badge(f), text, count=1)
    return LANGUAGES_BADGE_RE.sub(lambda m: m.group(0) + m.group(1) + tests_badge(f) + "\n", text, count=1)


VERSION_ROW_RE = re.compile(r"^(\| \*\*[^*|\n]+\*\* \| \*\*)(\d+(?:\.\d+)+)(\*\* · \[[^\n]*)$", re.M)      # | **Version** | **1.9.0** · [all releases](...)


def with_version(text, f):
    """The version of the row `Version` of the table "At a glance" (the first row of the first table after the lead): the one of tool_version.py."""
    return VERSION_ROW_RE.sub(lambda m: m.group(1) + f["version"] + m.group(3), text, count=1)


def render(lang, text, f):
    text = with_version(with_badge(text, f), f)
    new = block(lang, f)
    if BEGIN in text:
        return re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda m: new, text, flags=re.S)
    anchor = re.search(r"^## [^\n]*\n\n\| \| \|\n\|---\|---\|\n(?:\|[^\n]*\n)+\n", text, re.M)      # the "At a glance" table
    if not anchor:
        raise SystemExit("README without the At a glance table")
    return text[:anchor.end()] + new + "\n\n" + text[anchor.end():]


def main():
    check = "--check" in sys.argv
    f = facts()
    bad = []
    for lang, suffix in SUFFIX.items():
        path = ROOT / f"README{suffix}.md"
        old = path.read_text(encoding="utf-8")
        new = render(lang, old, f)
        if new != old:
            if check:
                bad.append(path.name)
            else:
                path.write_text(new, encoding="utf-8")
                print("written", path.name)
    if bad:
        print("GLANCE=FAIL out of date:", ", ".join(bad), "(run tools/make_glance.py)")
        return 1
    print("GLANCE=PASS" if check else "GLANCE=WRITTEN", f"({f['tests']} tests, {f['settings']} settings, v{f['version']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
