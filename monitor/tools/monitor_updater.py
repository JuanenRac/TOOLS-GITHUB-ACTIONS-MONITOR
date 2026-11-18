#!/usr/bin/env python3
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""The updater of the GitHub Actions monitor: ONE file, standard library only, that works on any installed version of the monitor.

  py -3 monitor_updater.py                 opens the updater in your browser (a page on 127.0.0.1 that lives only while this runs)
  py -3 monitor_updater.py --tk            the same in a window (needs Tkinter)
  py -3 monitor_updater.py --console       the same as a text menu (servers, SSH, containers)
  py -3 monitor_updater.py status|releases|plan|apply|migrate|rollback|history   [options]      (the same engine, one answer per command)

It detects the installation (version, edition, configuration, data, whether the monitor runs, container or service), lists every version published on GitHub, lets you choose the target, shows the PLAN
(a dry run: what changes in YOUR configuration, what changes of behaviour you will notice, every incoherence found) and applies it with a copy first, a check of the SHA-256 against SHA256SUMS, a safe
unpacking into a new folder, the migration of the configuration declared in the registry of migrations (JSON, versioned in every release), your own changes in the launchers kept, the start and the check of
/api/health, and an automatic return to the previous state if anything fails. It never updates by itself: only when you ask. It never deletes: what is replaced goes to the folder of copies.

Options common to the commands
  --dir FOLDER        the installation (default: the folder this file lives in, or the current one, looking upwards)
  --to VERSION        the target (default: the latest published)       --zip FILE   use this zip instead of GitHub (offline)      --sha256 HEX   the expected SHA-256 of --zip
  --dry-run           (apply) only show the plan                       --yes        do not ask for confirmation                     --json         the answer as one JSON document
  --keep-old-defaults write the old default of every setting you never set, so the behaviour does not change
  --adopt-new-defaults  also move the settings that still hold the old default to the new default
  --start             start the monitor after the update and check /api/health      --allow-downgrade   permit a lower version   --backups DIR   folder of copies (default: <install>/update_backups)
  --lang CODE         en es de fr it ja zh pt

Exit codes (stable): 0 done (or nothing to do); 2 wrong use; 3 blocked by a check (nothing changed); 4 the download, the SHA-256 or the zip failed (nothing changed); 5 the update failed and the previous state
was restored; 6 the update failed AND the automatic return failed (the copy is intact: restore it by hand); 7 no connection to GitHub and no zip given; 8 not confirmed.
"""
import argparse
import contextlib
import difflib
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

UPDATER_VERSION = "1.0"
REPO = "JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR"
ZIP_NAME = "github_actions_monitor.zip"
SUMS_NAME = "SHA256SUMS"
TOP = "github_actions_monitor"
BACKUPS_NAME = "update_backups"
HISTORY_NAME = "update_history.jsonl"
UA = "monitor-updater"
DOWNLOAD_HOSTS = ("github.com", "githubusercontent.com", "api.github.com")
MAX_ZIP = 300 * 1024 * 1024
MAX_UNPACKED = 600 * 1024 * 1024
MAX_FILES = 20000
MAX_RATIO = 300

OK, USAGE, BLOCKED, FETCH_FAILED, ROLLED_BACK, ROLLBACK_FAILED, OFFLINE, NOT_CONFIRMED = 0, 2, 3, 4, 5, 6, 7, 8

#: the folders of the product (replaced by an update); everything else of the root that is not a launcher or a document belongs to the person
PRODUCT_DIRS = ("src", "bin", "assets", "docs", "tools", "tests", "skills")
#: files of the root of the product that an update replaces
PRODUCT_ROOT_SUFFIXES = (".bat", ".sh", ".command", ".txt", ".md")
PRODUCT_ROOT_NAMES = ("LICENSE", "NOTICE", "AUTHORS", "CHANGELOG.md", "README.txt")
#: the same table as util/paths.py (kind of file by name): config, ai, logs, data. A test keeps both in step.
USER_RULES = (
    ("config", r"actions_monitor\.json|targets\.json|ecosystems\.json|profiles\.json|quotas\.json|lessons\.json|lessons_rules\.json|config_backups|paths\.json"),
    ("ai", r"ALERTS_BRIEF\.md|ai_alerts\.jsonl|ai_alerts_state\.json|ai_heartbeat\.json|ai_hook_state\.json|ai_notify\.jsonl|ai_notify_state\.json|ci_red\.json|INDEX\.json|LESSONS\.md"),
    ("logs", r"actions_monitor_log\.txt|ai_actions_log\.jsonl|github_actions_log\.jsonl|auth_audit\.jsonl|loop\.log"),
    ("data", r"etag_cache\.json|events_monitor\.jsonl|events_state\.json|eventos_monitor\.jsonl|eventos_estado\.json|analytics_history\.json|sentinel_cache\.json|sentinel_history\.json|"
            r"sentinel_ai_cache\.json|collab_state\.json|security_state\.json|supply_state\.json|delivery_state\.json|alert_mutes\.json|failures\.jsonl|update_check\.json|welcome_state\.json|orgs_state\.json|degraded\.json|targets\.candidates\.json|"
            r"storage\.sqlite3|org_logo\.(?:png|jpg|webp|svg|tmp)|access_token|credential|accounts|state|secrets|_global|_no_workspace|update_history\.jsonl"),
)
_USER_RE = tuple((kind, re.compile(r"^(?:" + body + r")\Z")) for kind, body in USER_RULES)
_VARIANT = re.compile(r"_(lite|demo)(?=\.|$)")
CONFIG_NAMES = ("actions_monitor.json", "actions_monitor_lite.json")
SECRET_WORDS = re.compile(r"secret|token|password|passwd|key|credential", re.I)
EXCLUDE_DIRS = {"__pycache__", BACKUPS_NAME, ".git"}
EXCLUDE_FROM_COPY = ("logs",)


class UpdaterError(Exception):
    """A failure with a stable exit code and a message key."""

    def __init__(self, code, message, key=None):
        super().__init__(message)
        self.code, self.key = code, key

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Texts of the updater in the eight languages (its own catalogue: this file must work alone on any installed version).
# ---------------------------------------------------------------------------------------------------------------------------------------------
LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
_CAT = {}


def _add(key, en, es, de, fr, it, ja, zh, pt):
    for lang, text in zip(LANGS, (en, es, de, fr, it, ja, zh, pt)):
        _CAT.setdefault(lang, {})[key] = text


_add("app.title", "Monitor updater", "Actualizador del monitor", "Monitor-Updater", "Mise à jour du moniteur", "Aggiornatore del monitor", "モニター アップデーター", "监视器更新程序", "Atualizador do monitor")
_add("lbl.installed", "Installed version", "Versión instalada", "Installierte Version", "Version installée", "Versione installata", "インストール済みバージョン", "已安装版本", "Versão instalada")
_add("lbl.folder", "Folder", "Carpeta", "Ordner", "Dossier", "Cartella", "フォルダー", "文件夹", "Pasta")
_add("lbl.edition", "Edition", "Edición", "Edition", "Édition", "Edizione", "エディション", "版本类型", "Edição")
_add("lbl.config", "Configuration", "Configuración", "Konfiguration", "Configuration", "Configurazione", "設定", "配置", "Configuração")
_add("lbl.data", "Data", "Datos", "Daten", "Données", "Dati", "データ", "数据", "Dados")
_add("lbl.running", "Monitor running", "Monitor en marcha", "Monitor läuft", "Moniteur en marche", "Monitor in esecuzione", "モニター稼働中", "监视器运行中", "Monitor em execução")
_add("lbl.mode", "Mode", "Modo", "Modus", "Mode", "Modalità", "モード", "模式", "Modo")
_add("lbl.target", "Target version", "Versión de destino", "Zielversion", "Version cible", "Versione di destinazione", "対象バージョン", "目标版本", "Versão de destino")
_add("lbl.source", "Source", "Origen", "Quelle", "Source", "Origine", "取得元", "来源", "Origem")
_add("lbl.latest", "latest", "última", "neueste", "dernière", "ultima", "最新", "最新", "última")
_add("lbl.current", "installed", "instalada", "installiert", "installée", "installata", "導入済み", "已安装", "instalada")
_add("lbl.newer", "newer", "más nueva", "neuer", "plus récente", "più nuova", "新しい", "较新", "mais nova")
_add("lbl.older", "older", "más antigua", "älter", "plus ancienne", "più vecchia", "古い", "较旧", "mais antiga")
_add("lbl.yes", "yes", "sí", "ja", "oui", "sì", "はい", "是", "sim")
_add("lbl.no", "no", "no", "nein", "non", "no", "いいえ", "否", "não")
_add("lbl.unknown", "unknown", "desconocido", "unbekannt", "inconnu", "sconosciuto", "不明", "未知", "desconhecido")
_add("lbl.none", "none", "ninguno", "keine", "aucun", "nessuno", "なし", "无", "nenhum")
_add("mode.folder", "plain folder", "carpeta normal", "normaler Ordner", "dossier simple", "cartella normale", "通常のフォルダー", "普通文件夹", "pasta normal")
_add("mode.docker", "container (Docker)", "contenedor (Docker)", "Container (Docker)", "conteneur (Docker)", "contenitore (Docker)", "コンテナー（Docker）", "容器（Docker）", "contentor (Docker)")
_add("mode.service", "service on this computer", "servicio en este equipo", "Dienst auf diesem Rechner", "service sur cet ordinateur", "servizio su questo computer", "このPCのサービス", "本机服务", "serviço neste computador")
_add("btn.refresh", "Detect again", "Detectar de nuevo", "Erneut erkennen", "Détecter à nouveau", "Rileva di nuovo", "再検出", "重新检测", "Detetar de novo")
_add("btn.plan", "Show the plan (dry run)", "Ver el plan (ensayo)", "Plan anzeigen (Probelauf)", "Voir le plan (essai)", "Mostra il piano (prova)", "計画を表示（ドライラン）", "查看计划（试运行）", "Ver o plano (ensaio)")
_add("btn.apply", "Update now", "Actualizar ahora", "Jetzt aktualisieren", "Mettre à jour", "Aggiorna ora", "今すぐ更新", "立即更新", "Atualizar agora")
_add("btn.rollback", "Go back to the previous version", "Volver a la versión anterior", "Zur vorherigen Version zurück", "Revenir à la version précédente", "Torna alla versione precedente", "前のバージョンに戻す", "回到上一个版本", "Voltar à versão anterior")
_add("btn.history", "History", "Historial", "Verlauf", "Historique", "Cronologia", "履歴", "历史", "Histórico")
_add("btn.quit", "Quit", "Salir", "Beenden", "Quitter", "Esci", "終了", "退出", "Sair")
_add("btn.zip", "Use a zip I already have", "Usar un zip que ya tengo", "Vorhandenes Zip verwenden", "Utiliser un zip que j'ai déjà", "Usa uno zip che ho già", "手元のzipを使う", "使用已有的 zip", "Usar um zip que já tenho")
_add("opt.keep_old", "Keep the old defaults", "Conservar los defectos antiguos", "Alte Standardwerte beibehalten", "Conserver les anciennes valeurs par défaut", "Mantieni i vecchi valori predefiniti", "古い既定値を保持", "保留旧默认值", "Manter os defeitos antigos")
_add("opt.adopt_new", "Adopt the new defaults", "Adoptar los nuevos defectos", "Neue Standardwerte übernehmen", "Adopter les nouvelles valeurs par défaut", "Adotta i nuovi valori predefiniti", "新しい既定値を採用", "采用新默认值", "Adotar os novos defeitos")
_add("opt.start", "Start the monitor afterwards and check it", "Arrancar el monitor después y comprobarlo", "Monitor danach starten und prüfen", "Démarrer ensuite le moniteur et le vérifier", "Avvia poi il monitor e verificalo", "更新後にモニターを起動して確認", "更新后启动监视器并检查", "Arrancar o monitor depois e verificá-lo")
_add("opt.policy_note", "By default what you set yourself is kept and the new defaults apply only to what you never set.", "Por defecto se conserva lo que tú fijaste y los nuevos defectos solo se aplican a lo que nunca definiste.", "Standardmäßig bleibt, was du selbst festgelegt hast; neue Standardwerte gelten nur für Unbestimmtes.", "Par défaut, ce que vous avez fixé est conservé et les nouvelles valeurs ne s'appliquent qu'à ce que vous n'avez jamais défini.", "Di default si conserva ciò che hai impostato e i nuovi valori valgono solo per ciò che non hai mai definito.", "既定では自分で設定した値は保持され、新しい既定値は未設定の項目にだけ適用されます。", "默认保留你自己设置的值，新默认值只用于你从未设置的项目。", "Por defeito mantém-se o que definiu e os novos defeitos só se aplicam ao que nunca definiu.")
_add("sec.releases", "Versions on GitHub", "Versiones en GitHub", "Versionen auf GitHub", "Versions sur GitHub", "Versioni su GitHub", "GitHub のバージョン", "GitHub 上的版本", "Versões no GitHub")
_add("sec.plan", "Plan", "Plan", "Plan", "Plan", "Piano", "計画", "计划", "Plano")
_add("sec.checks", "Checks", "Comprobaciones", "Prüfungen", "Vérifications", "Controlli", "チェック", "检查", "Verificações")
_add("sec.config", "What changes in your configuration", "Qué cambia en tu configuración", "Was sich in deiner Konfiguration ändert", "Ce qui change dans votre configuration", "Cosa cambia nella tua configurazione", "設定で変わること", "你的配置有哪些变化", "O que muda na sua configuração")
_add("sec.notices", "Changes of behaviour", "Cambios de comportamiento", "Verhaltensänderungen", "Changements de comportement", "Cambiamenti di comportamento", "動作の変更", "行为变化", "Mudanças de comportamento")
_add("sec.steps", "Steps", "Pasos", "Schritte", "Étapes", "Passaggi", "手順", "步骤", "Passos")
_add("sec.progress", "Progress", "Progreso", "Fortschritt", "Progression", "Avanzamento", "進行状況", "进度", "Progresso")
_add("sec.result", "Result", "Resultado", "Ergebnis", "Résultat", "Risultato", "結果", "结果", "Resultado")
_add("sev.block", "BLOCKS", "BLOQUEA", "BLOCKIERT", "BLOQUE", "BLOCCA", "ブロック", "阻止", "BLOQUEIA")
_add("sev.warn", "warning", "aviso", "Warnung", "avertissement", "avviso", "警告", "警告", "aviso")
_add("sev.info", "info", "info", "Info", "info", "info", "情報", "信息", "info")
_add("dir.upgrade", "update", "actualización", "Aktualisierung", "mise à jour", "aggiornamento", "更新", "升级", "atualização")
_add("dir.downgrade", "DOWNGRADE", "VUELTA A UNA VERSIÓN ANTERIOR", "DOWNGRADE", "RETOUR À UNE VERSION ANTÉRIEURE", "RITORNO A UNA VERSIONE PRECEDENTE", "ダウングレード", "降级", "REGRESSO A UMA VERSÃO ANTERIOR")
_add("dir.same", "same version (reinstall)", "misma versión (reinstalar)", "gleiche Version (neu installieren)", "même version (réinstaller)", "stessa versione (reinstalla)", "同じバージョン（再インストール）", "相同版本（重新安装）", "mesma versão (reinstalar)")
_add("c.handover", "The monitor on port {port} stops by itself, the update is applied and it starts again; if it does not start, the previous version comes back.", "El monitor del puerto {port} se detiene solo, se aplica la actualización y vuelve a arrancar; si no arranca, vuelve la versión anterior.", "Der Monitor auf Port {port} beendet sich selbst, das Update wird eingespielt und er startet neu; startet er nicht, kommt die vorherige Version zurück.", "Le moniteur du port {port} s'arrête de lui-même, la mise à jour est appliquée et il redémarre ; s'il ne démarre pas, la version précédente revient.", "Il monitor sulla porta {port} si ferma da solo, l'aggiornamento viene applicato e riparte; se non parte, torna la versione precedente.", "ポート {port} のモニターは自動的に停止し、更新が適用されて再起動します。起動しない場合は以前のバージョンに戻ります。", "端口 {port} 上的监视器会自行停止，应用更新后重新启动；若无法启动，则恢复到之前的版本。", "O monitor da porta {port} para sozinho, a atualização é aplicada e volta a arrancar; se não arrancar, regressa a versão anterior.")
_add("c.running", "The monitor is running on port {port}: stop it before updating.", "El monitor está en marcha en el puerto {port}: páralo antes de actualizar.", "Der Monitor läuft auf Port {port}: beende ihn vor dem Update.", "Le moniteur tourne sur le port {port} : arrêtez-le avant de mettre à jour.", "Il monitor è in esecuzione sulla porta {port}: fermalo prima di aggiornare.", "モニターがポート {port} で稼働中です。更新前に停止してください。", "监视器正在端口 {port} 运行：更新前请先停止。", "O monitor está em execução na porta {port}: pare-o antes de atualizar.")
_add("c.sha", "The SHA-256 of the zip does not match the published one: nothing was changed.", "El SHA-256 del zip no coincide con el publicado: no se cambió nada.", "Der SHA-256 des Zips stimmt nicht mit dem veröffentlichten überein: nichts wurde geändert.", "Le SHA-256 du zip ne correspond pas à celui publié : rien n'a été modifié.", "Lo SHA-256 dello zip non corrisponde a quello pubblicato: nulla è stato modificato.", "zipのSHA-256が公開値と一致しません。何も変更していません。", "zip 的 SHA-256 与发布值不符：未做任何更改。", "O SHA-256 do zip não coincide com o publicado: nada foi alterado.")
_add("c.unverified", "This zip cannot be checked against a published SHA-256 (local file without SHA256SUMS).", "Este zip no se puede comprobar con un SHA-256 publicado (fichero local sin SHA256SUMS).", "Dieses Zip lässt sich nicht gegen einen veröffentlichten SHA-256 prüfen (lokale Datei ohne SHA256SUMS).", "Ce zip ne peut pas être vérifié avec un SHA-256 publié (fichier local sans SHA256SUMS).", "Questo zip non si può verificare con uno SHA-256 pubblicato (file locale senza SHA256SUMS).", "このzipは公開SHA-256で検証できません（SHA256SUMSのないローカルファイル）。", "无法用已发布的 SHA-256 校验此 zip（本地文件没有 SHA256SUMS）。", "Este zip não pode ser verificado com um SHA-256 publicado (ficheiro local sem SHA256SUMS).")
_add("c.disk", "Not enough free space: {need} MB needed, {free} MB free in {where}.", "No hay espacio libre suficiente: hacen falta {need} MB y quedan {free} MB en {where}.", "Zu wenig freier Platz: {need} MB nötig, {free} MB frei in {where}.", "Espace libre insuffisant : {need} Mo nécessaires, {free} Mo libres dans {where}.", "Spazio libero insufficiente: servono {need} MB, ne restano {free} MB in {where}.", "空き容量が不足: {where} に {need} MB 必要ですが {free} MB しかありません。", "可用空间不足：{where} 需要 {need} MB，仅剩 {free} MB。", "Sem espaço livre suficiente: são precisos {need} MB e restam {free} MB em {where}.")
_add("c.perm", "No permission to write in {where}.", "Sin permiso para escribir en {where}.", "Keine Schreibberechtigung in {where}.", "Pas d'autorisation d'écriture dans {where}.", "Nessun permesso di scrittura in {where}.", "{where} への書き込み権限がありません。", "没有写入 {where} 的权限。", "Sem permissão para escrever em {where}.")
_add("c.db_newer", "The data are from a newer version (schema {have}) than the target understands (schema {want}): going back could damage them.", "Los datos son de una versión más nueva (esquema {have}) que la que entiende el destino (esquema {want}): volver atrás podría dañarlos.", "Die Daten stammen aus einer neueren Version (Schema {have}) als das Ziel versteht (Schema {want}): ein Zurückgehen könnte sie beschädigen.", "Les données viennent d'une version plus récente (schéma {have}) que celle comprise par la cible (schéma {want}) : revenir en arrière pourrait les abîmer.", "I dati sono di una versione più nuova (schema {have}) di quella capita dalla destinazione (schema {want}): tornare indietro potrebbe danneggiarli.", "データは対象より新しいバージョン（スキーマ {have}、対象は {want}）のものです。戻すとデータが壊れる恐れがあります。", "数据来自比目标更新的版本（架构 {have}，目标仅支持 {want}）：回退可能损坏数据。", "Os dados são de uma versão mais nova (esquema {have}) do que a de destino entende (esquema {want}): voltar atrás pode danificá-los.")
_add("c.unknown_key", "Setting {key} does not exist in {to}: it will be left as it is and ignored.", "El ajuste {key} no existe en {to}: se deja como está y se ignora.", "Die Einstellung {key} gibt es in {to} nicht: sie bleibt unverändert und wird ignoriert.", "Le réglage {key} n'existe pas dans {to} : il est laissé tel quel et ignoré.", "L'impostazione {key} non esiste in {to}: resta com'è e viene ignorata.", "設定 {key} は {to} に存在しません。そのまま残し、無視されます。", "设置 {key} 在 {to} 中不存在：保持原样并被忽略。", "A definição {key} não existe em {to}: fica como está e é ignorada.")
_add("c.range", "Setting {key} has a value ({value}) outside what {to} accepts ({rule}).", "El ajuste {key} tiene un valor ({value}) fuera de lo que acepta {to} ({rule}).", "Die Einstellung {key} hat einen Wert ({value}) außerhalb dessen, was {to} akzeptiert ({rule}).", "Le réglage {key} a une valeur ({value}) hors de ce qu'accepte {to} ({rule}).", "L'impostazione {key} ha un valore ({value}) fuori da ciò che {to} accetta ({rule}).", "設定 {key} の値（{value}）は {to} が受け付ける範囲（{rule}）外です。", "设置 {key} 的值（{value}）超出 {to} 接受的范围（{rule}）。", "A definição {key} tem um valor ({value}) fora do que {to} aceita ({rule}).")
_add("c.type", "Setting {key} has the wrong type for {to} (expected {kind}).", "El ajuste {key} tiene un tipo que {to} no espera (se esperaba {kind}).", "Die Einstellung {key} hat für {to} den falschen Typ (erwartet: {kind}).", "Le réglage {key} n'a pas le bon type pour {to} (attendu : {kind}).", "L'impostazione {key} ha un tipo sbagliato per {to} (atteso: {kind}).", "設定 {key} の型が {to} に合いません（期待: {kind}）。", "设置 {key} 的类型与 {to} 不符（应为 {kind}）。", "A definição {key} tem o tipo errado para {to} (esperado: {kind}).")
_add("c.dup", "The key {key} appears more than once in {file}: only the last one counts.", "La clave {key} aparece más de una vez en {file}: solo cuenta la última.", "Der Schlüssel {key} kommt mehrfach in {file} vor: nur der letzte zählt.", "La clé {key} apparaît plusieurs fois dans {file} : seule la dernière compte.", "La chiave {key} compare più volte in {file}: conta solo l'ultima.", "キー {key} が {file} に複数回あります。最後のものだけが有効です。", "键 {key} 在 {file} 中出现多次：只有最后一个有效。", "A chave {key} aparece mais do que uma vez em {file}: só conta a última.")
_add("c.badjson", "{file} is not valid JSON ({error}): its configuration cannot be migrated.", "{file} no es un JSON válido ({error}): su configuración no se puede migrar.", "{file} ist kein gültiges JSON ({error}): die Konfiguration kann nicht migriert werden.", "{file} n'est pas un JSON valide ({error}) : sa configuration ne peut pas être migrée.", "{file} non è un JSON valido ({error}): la sua configurazione non si può migrare.", "{file} は有効なJSONではありません（{error}）。設定を移行できません。", "{file} 不是有效的 JSON（{error}）：无法迁移其配置。", "{file} não é um JSON válido ({error}): a sua configuração não pode ser migrada.")
_add("c.edition", "The target has no files for the edition you use ({edition}).", "El destino no trae los ficheros de la edición que usas ({edition}).", "Das Ziel enthält keine Dateien für die verwendete Edition ({edition}).", "La cible n'a pas les fichiers de l'édition utilisée ({edition}).", "La destinazione non ha i file dell'edizione che usi ({edition}).", "対象には使用中のエディション（{edition}）のファイルがありません。", "目标没有你所用版本（{edition}）的文件。", "O destino não traz os ficheiros da edição que usa ({edition}).")
_add("c.path", "The path {path} (setting {key}) does not exist.", "La ruta {path} (ajuste {key}) no existe.", "Der Pfad {path} (Einstellung {key}) existiert nicht.", "Le chemin {path} (réglage {key}) n'existe pas.", "Il percorso {path} (impostazione {key}) non esiste.", "パス {path}（設定 {key}）が存在しません。", "路径 {path}（设置 {key}）不存在。", "O caminho {path} (definição {key}) não existe.")
_add("c.port", "Port {port} is used by something that is not this monitor.", "El puerto {port} lo usa algo que no es este monitor.", "Port {port} wird von etwas anderem als diesem Monitor benutzt.", "Le port {port} est utilisé par autre chose que ce moniteur.", "La porta {port} è usata da qualcosa che non è questo monitor.", "ポート {port} はこのモニター以外が使用しています。", "端口 {port} 被此监视器以外的程序占用。", "A porta {port} é usada por algo que não é este monitor.")
_add("c.downgrade", "You are going back from {from_} to {to}: the configuration is NOT converted back and newer settings stay unknown to the older version.", "Vuelves de {from_} a {to}: la configuración NO se convierte hacia atrás y los ajustes nuevos serán desconocidos para la versión antigua.", "Du gehst von {from_} auf {to} zurück: die Konfiguration wird NICHT zurückkonvertiert, neuere Einstellungen bleiben der älteren Version unbekannt.", "Vous revenez de {from_} à {to} : la configuration n'est PAS reconvertie et les réglages récents resteront inconnus de l'ancienne version.", "Torni da {from_} a {to}: la configurazione NON viene riconvertita e le impostazioni nuove resteranno sconosciute alla versione vecchia.", "{from_} から {to} へ戻します。設定は逆変換されず、新しい設定は古い版では認識されません。", "从 {from_} 回退到 {to}：配置不会反向转换，较新的设置旧版本无法识别。", "Vai de {from_} para {to}: a configuração NÃO é convertida de volta e as definições novas ficam desconhecidas da versão antiga.")
_add("c.container", "This is a container: the image cannot be replaced from inside. Update the image and keep the volumes; use the migrate command on the /config volume.", "Esto es un contenedor: la imagen no se puede cambiar desde dentro. Actualiza la imagen y conserva los volúmenes; usa el comando migrate sobre el volumen /config.", "Dies ist ein Container: das Image lässt sich von innen nicht ersetzen. Aktualisiere das Image, behalte die Volumes; nutze den Befehl migrate auf dem Volume /config.", "Ceci est un conteneur : l'image ne peut pas être remplacée de l'intérieur. Mettez l'image à jour, gardez les volumes ; utilisez la commande migrate sur le volume /config.", "Questo è un contenitore: l'immagine non si può sostituire dall'interno. Aggiorna l'immagine, conserva i volumi; usa il comando migrate sul volume /config.", "これはコンテナーです。内部からイメージを置き換えられません。イメージを更新してボリュームは保持し、/config ボリュームに migrate コマンドを使ってください。", "这是容器：无法从内部替换镜像。请更新镜像并保留卷；对 /config 卷使用 migrate 命令。", "Isto é um contentor: a imagem não se pode substituir por dentro. Atualize a imagem, mantenha os volumes; use o comando migrate no volume /config.")
_add("c.launcher", "Your launcher {name} has changes of your own: they are kept ({how}).", "Tu lanzador {name} tiene cambios tuyos: se conservan ({how}).", "Dein Starter {name} enthält eigene Änderungen: sie bleiben erhalten ({how}).", "Votre lanceur {name} contient vos modifications : elles sont conservées ({how}).", "Il tuo avviatore {name} ha modifiche tue: vengono conservate ({how}).", "起動スクリプト {name} に独自の変更があります。保持されます（{how}）。", "你的启动脚本 {name} 含有你自己的修改：将被保留（{how}）。", "O seu lançador {name} tem alterações suas: são mantidas ({how}).")
_add("c.registry_gap", "The registry of migrations has no entry for {versions}: the configuration is only checked, not converted, for those versions.", "El registro de migraciones no tiene entrada para {versions}: para esas versiones la configuración solo se comprueba, no se convierte.", "Das Migrationsregister hat keinen Eintrag für {versions}: für diese Versionen wird die Konfiguration nur geprüft, nicht umgewandelt.", "Le registre de migrations n'a pas d'entrée pour {versions} : pour ces versions la configuration est seulement vérifiée, pas convertie.", "Il registro delle migrazioni non ha voci per {versions}: per quelle versioni la configurazione è solo controllata, non convertita.", "移行レジストリに {versions} の項目がありません。それらのバージョンでは設定は確認のみで変換されません。", "迁移注册表中没有 {versions} 的条目：这些版本的配置只检查，不转换。", "O registo de migrações não tem entrada para {versions}: para essas versões a configuração só é verificada, não convertida.")
_add("c.pending", "A previous update did not finish ({backup}). Resume it or go back before starting another one.", "Una actualización anterior no terminó ({backup}). Reanúdala o vuelve atrás antes de empezar otra.", "Ein früheres Update wurde nicht beendet ({backup}). Setze es fort oder gehe zurück, bevor du ein neues beginnst.", "Une mise à jour précédente n'est pas terminée ({backup}). Reprenez-la ou revenez en arrière avant d'en lancer une autre.", "Un aggiornamento precedente non è terminato ({backup}). Riprendilo o torna indietro prima di iniziarne un altro.", "前回の更新が完了していません（{backup}）。再開するか元に戻してから新しい更新を始めてください。", "上一次更新尚未完成（{backup}）：请先继续或回退，再开始新的更新。", "Uma atualização anterior não terminou ({backup}). Retome-a ou volte atrás antes de iniciar outra.")
_add("c.locked", "Another updater is working on this folder.", "Otro actualizador está trabajando en esta carpeta.", "Ein anderer Updater arbeitet in diesem Ordner.", "Un autre outil de mise à jour travaille dans ce dossier.", "Un altro aggiornatore sta lavorando in questa cartella.", "別のアップデーターがこのフォルダーで作業中です。", "另一个更新程序正在处理此文件夹。", "Outro atualizador está a trabalhar nesta pasta.")
_add("c.required", "Version {need} must be installed first (or update from a version at least {need}).", "Hay que instalar antes la versión {need} (o actualizar desde una versión de al menos {need}).", "Zuerst muss Version {need} installiert werden (oder von mindestens {need} aktualisieren).", "Il faut d'abord installer la version {need} (ou mettre à jour depuis au moins {need}).", "Occorre prima installare la versione {need} (o aggiornare da almeno {need}).", "先にバージョン {need} をインストールしてください（または {need} 以上から更新）。", "需要先安装版本 {need}（或从至少 {need} 的版本更新）。", "É preciso instalar antes a versão {need} (ou atualizar a partir de pelo menos {need}).")
_add("c.same_vm", "Nothing to do: version {version} is already installed.", "Nada que hacer: la versión {version} ya está instalada.", "Nichts zu tun: Version {version} ist bereits installiert.", "Rien à faire : la version {version} est déjà installée.", "Niente da fare: la versione {version} è già installata.", "何もする必要はありません。バージョン {version} は導入済みです。", "无需操作：已安装版本 {version}。", "Nada a fazer: a versão {version} já está instalada.")
_add("ch.renamed", "{old} was renamed to {new}: your value moves.", "{old} se renombró a {new}: tu valor se traslada.", "{old} wurde in {new} umbenannt: dein Wert wird übernommen.", "{old} a été renommé en {new} : votre valeur est déplacée.", "{old} è stato rinominato in {new}: il tuo valore viene spostato.", "{old} は {new} に改名されました。値は移されます。", "{old} 已更名为 {new}：你的值会迁移。", "{old} foi renomeado para {new}: o seu valor é transferido.")
_add("ch.removed", "{key} no longer exists: it is taken out of the file (the copy before the update keeps it).", "{key} ya no existe: se quita del fichero (la copia previa lo conserva).", "{key} gibt es nicht mehr: es wird aus der Datei entfernt (die Sicherung davor behält es).", "{key} n'existe plus : il est retiré du fichier (la copie préalable le garde).", "{key} non esiste più: viene tolto dal file (la copia precedente lo conserva).", "{key} は廃止されました。ファイルから取り除きます（更新前のコピーに残ります）。", "{key} 已不存在：从文件中移除（更新前的副本保留它）。", "{key} já não existe: é retirado do ficheiro (a cópia prévia conserva-o).")
_add("ch.pinned", "{key}: the old default ({old}) is written so the behaviour does not change (the new default is {new}).", "{key}: se escribe el antiguo defecto ({old}) para que el comportamiento no cambie (el nuevo defecto es {new}).", "{key}: der alte Standardwert ({old}) wird eingetragen, damit sich das Verhalten nicht ändert (neuer Standard: {new}).", "{key} : l'ancienne valeur par défaut ({old}) est écrite pour que le comportement ne change pas (la nouvelle est {new}).", "{key}: si scrive il vecchio valore predefinito ({old}) perché il comportamento non cambi (il nuovo è {new}).", "{key}: 動作を変えないよう旧既定値（{old}）を書き込みます（新既定値は {new}）。", "{key}：写入旧默认值（{old}）以保持行为不变（新默认值为 {new}）。", "{key}: escreve-se o antigo defeito ({old}) para o comportamento não mudar (o novo defeito é {new}).")
_add("ch.new_default", "{key} was never set by you: the new default ({new}) applies (before: {old}).", "{key} nunca lo definiste: se aplica el nuevo defecto ({new}) (antes: {old}).", "{key} hast du nie gesetzt: der neue Standard ({new}) gilt (vorher: {old}).", "{key} n'a jamais été défini par vous : la nouvelle valeur par défaut ({new}) s'applique (avant : {old}).", "{key} non l'hai mai impostato: vale il nuovo predefinito ({new}) (prima: {old}).", "{key} は未設定のため、新既定値（{new}）が適用されます（以前: {old}）。", "{key} 你从未设置：将采用新默认值（{new}）（之前：{old}）。", "{key} nunca foi definido por si: aplica-se o novo defeito ({new}) (antes: {old}).")
_add("ch.kept", "{key}: you set {old} yourself; it is kept (the new default is {new}).", "{key}: lo fijaste tú en {old}; se conserva (el nuevo defecto es {new}).", "{key}: du hast {old} selbst gesetzt; es bleibt (neuer Standard: {new}).", "{key} : vous l'avez fixé à {old} ; il est conservé (la nouvelle valeur par défaut est {new}).", "{key}: l'hai impostato tu a {old}; viene conservato (il nuovo predefinito è {new}).", "{key}: 自分で {old} に設定済みのため保持します（新既定値は {new}）。", "{key}：你自己设为 {old}，予以保留（新默认值为 {new}）。", "{key}: definiu-o você em {old}; é mantido (o novo defeito é {new}).")
_add("ch.adopted", "{key}: changed from {old} to the new default {new}.", "{key}: pasa de {old} al nuevo defecto {new}.", "{key}: von {old} auf den neuen Standard {new} geändert.", "{key} : passe de {old} à la nouvelle valeur par défaut {new}.", "{key}: passa da {old} al nuovo predefinito {new}.", "{key}: {old} から新既定値 {new} に変更します。", "{key}：从 {old} 改为新默认值 {new}。", "{key}: passa de {old} para o novo defeito {new}.")
_add("ch.none", "Your configuration needs no change.", "Tu configuración no necesita cambios.", "Deine Konfiguration braucht keine Änderung.", "Votre configuration n'a besoin d'aucun changement.", "La tua configurazione non richiede modifiche.", "設定の変更は不要です。", "你的配置无需更改。", "A sua configuração não precisa de alterações.")
_add("st.lock", "Locking the folder", "Bloqueando la carpeta", "Ordner sperren", "Verrouillage du dossier", "Blocco della cartella", "フォルダーをロック", "锁定文件夹", "A bloquear a pasta")
_add("st.download", "Downloading and checking the zip", "Descargando y comprobando el zip", "Zip herunterladen und prüfen", "Téléchargement et vérification du zip", "Scarico e verifica dello zip", "zipをダウンロードして検証", "下载并校验 zip", "A descarregar e verificar o zip")
_add("st.extract", "Unpacking into a new folder", "Extrayendo en una carpeta nueva", "In neuen Ordner entpacken", "Extraction dans un nouveau dossier", "Estrazione in una nuova cartella", "新しいフォルダーに展開", "解压到新文件夹", "A extrair para uma pasta nova")
_add("st.backup", "Copy of the current installation", "Copia de la instalación actual", "Kopie der aktuellen Installation", "Copie de l'installation actuelle", "Copia dell'installazione attuale", "現在のインストールのコピー", "备份当前安装", "Cópia da instalação atual")
_add("st.copy", "Copying the new product", "Copiando el producto nuevo", "Neues Produkt kopieren", "Copie du nouveau produit", "Copia del nuovo prodotto", "新しい製品をコピー", "复制新产品", "A copiar o produto novo")
_add("st.retire", "Setting aside modules that no longer exist", "Apartando módulos que ya no existen", "Nicht mehr vorhandene Module beiseite legen", "Mise à l'écart des modules disparus", "Messa da parte dei moduli non più esistenti", "不要になったモジュールを退避", "移开已不存在的模块", "A pôr de lado módulos que já não existem")
_add("st.launchers", "Restoring your changes in the launchers", "Restaurando tus cambios en los lanzadores", "Eigene Änderungen in den Startern wiederherstellen", "Restauration de vos modifications des lanceurs", "Ripristino delle tue modifiche negli avviatori", "起動スクリプトの独自変更を復元", "恢复启动脚本中的自定义修改", "A restaurar as suas alterações nos lançadores")
_add("st.config", "Migrating the configuration", "Migrando la configuración", "Konfiguration migrieren", "Migration de la configuration", "Migrazione della configurazione", "設定を移行", "迁移配置", "A migrar a configuração")
_add("st.layout", "Tidying the folder layout", "Ordenando la estructura de carpetas", "Ordnerstruktur aufräumen", "Rangement de l'arborescence", "Riordino della struttura delle cartelle", "フォルダー構成を整理", "整理文件夹结构", "A arrumar a estrutura de pastas")
_add("st.verify", "Checking the installed version", "Comprobando la versión instalada", "Installierte Version prüfen", "Vérification de la version installée", "Verifica della versione installata", "導入バージョンを確認", "检查已安装版本", "A verificar a versão instalada")
_add("st.start", "Starting the monitor and checking /api/health", "Arrancando el monitor y comprobando /api/health", "Monitor starten und /api/health prüfen", "Démarrage du moniteur et contrôle de /api/health", "Avvio del monitor e controllo di /api/health", "モニターを起動し /api/health を確認", "启动监视器并检查 /api/health", "A arrancar o monitor e a verificar /api/health")
_add("st.rollback", "Going back automatically", "Volviendo atrás automáticamente", "Automatisch zurückgehen", "Retour automatique en arrière", "Ritorno automatico", "自動的に元へ戻しています", "正在自动回退", "A voltar atrás automaticamente")
_add("st.done", "done", "hecho", "erledigt", "fait", "fatto", "完了", "完成", "feito")
_add("st.skipped", "skipped", "omitido", "übersprungen", "ignoré", "saltato", "スキップ", "已跳过", "ignorado")
_add("st.failed", "FAILED", "FALLÓ", "FEHLGESCHLAGEN", "ÉCHEC", "FALLITO", "失敗", "失败", "FALHOU")
_add("r.ok", "Updated to {to}. A copy of what was there is in {backup}.", "Actualizado a {to}. La copia de lo que había está en {backup}.", "Auf {to} aktualisiert. Eine Kopie des Vorherigen liegt in {backup}.", "Mis à jour vers {to}. Une copie de l'existant se trouve dans {backup}.", "Aggiornato a {to}. Una copia di ciò che c'era è in {backup}.", "{to} に更新しました。以前の内容のコピーは {backup} にあります。", "已更新到 {to}。原有内容的副本在 {backup}。", "Atualizado para {to}. A cópia do que lá estava está em {backup}.")
_add("r.dry", "Dry run: nothing was changed in the installation.", "Ensayo: no se cambió nada en la instalación.", "Probelauf: an der Installation wurde nichts geändert.", "Essai : rien n'a été modifié dans l'installation.", "Prova: nulla è stato modificato nell'installazione.", "ドライラン: インストールは何も変更していません。", "试运行：未对安装做任何更改。", "Ensaio: nada foi alterado na instalação.")
_add("r.blocked", "It cannot be applied: {n} check(s) block it.", "No se puede aplicar: {n} comprobación(es) lo impiden.", "Nicht anwendbar: {n} Prüfung(en) blockieren.", "Impossible à appliquer : {n} vérification(s) bloquent.", "Non applicabile: {n} controllo/i lo bloccano.", "適用できません。{n} 件のチェックが阻止しています。", "无法应用：有 {n} 项检查阻止。", "Não pode ser aplicado: {n} verificação(ões) bloqueiam.")
_add("r.rolled", "It failed ({error}) and the previous state was restored automatically. Report in {backup}.", "Falló ({error}) y se restauró solo el estado anterior. Informe en {backup}.", "Fehlgeschlagen ({error}); der vorherige Zustand wurde automatisch wiederhergestellt. Bericht in {backup}.", "Échec ({error}) ; l'état précédent a été restauré automatiquement. Rapport dans {backup}.", "Fallito ({error}); lo stato precedente è stato ripristinato in automatico. Rapporto in {backup}.", "失敗しました（{error}）。以前の状態を自動で復元しました。レポート: {backup}", "失败（{error}），已自动恢复到之前的状态。报告在 {backup}。", "Falhou ({error}) e o estado anterior foi restaurado automaticamente. Relatório em {backup}.")
_add("r.rollback_failed", "It failed ({error}) and the automatic return ALSO failed ({error2}). Your copy is intact in {backup}: restore it by hand.", "Falló ({error}) y la vuelta automática TAMBIÉN falló ({error2}). Tu copia está intacta en {backup}: restáurala a mano.", "Fehlgeschlagen ({error}) und die automatische Rückkehr schlug AUCH fehl ({error2}). Deine Kopie liegt unversehrt in {backup}: stelle sie von Hand wieder her.", "Échec ({error}) et le retour automatique a AUSSI échoué ({error2}). Votre copie est intacte dans {backup} : restaurez-la à la main.", "Fallito ({error}) e anche il ritorno automatico è FALLITO ({error2}). La tua copia è intatta in {backup}: ripristinala a mano.", "失敗し（{error}）、自動復元も失敗しました（{error2}）。コピーは {backup} に無傷で残っています。手動で復元してください。", "失败（{error}），自动回退也失败了（{error2}）。你的副本完好保存在 {backup}：请手动恢复。", "Falhou ({error}) e o regresso automático TAMBÉM falhou ({error2}). A sua cópia está intacta em {backup}: restaure-a à mão.")
_add("r.rollback_ok", "Went back to {to}. What the failed state left is in {backup}.", "Se volvió a {to}. Lo que dejó el estado fallido está en {backup}.", "Zurück auf {to}. Was der fehlgeschlagene Zustand hinterließ, liegt in {backup}.", "Retour à {to}. Ce qu'a laissé l'état en échec est dans {backup}.", "Tornato a {to}. Ciò che ha lasciato lo stato fallito è in {backup}.", "{to} に戻しました。失敗した状態の残りは {backup} にあります。", "已回到 {to}。失败状态留下的内容在 {backup}。", "Voltou-se a {to}. O que o estado falhado deixou está em {backup}.")
_add("r.back_ok", "Went back to {to}. What you leave behind is in {backup}.", "Se volvió a {to}. Lo que dejas atrás está en {backup}.", "Zurück auf {to}. Was du hinter dir lässt, liegt in {backup}.", "Retour à {to}. Ce que vous laissez derrière est dans {backup}.", "Tornato a {to}. Ciò che lasci è in {backup}.", "{to} に戻しました。残したものは {backup} にあります。", "已回到 {to}。你放下的内容在 {backup}。", "Voltou-se a {to}. O que deixa para trás está em {backup}.")
_add("r.no_previous", "There is no earlier update to go back to.", "No hay ninguna actualización anterior a la que volver.", "Es gibt kein früheres Update, zu dem man zurückkehren könnte.", "Il n'y a aucune mise à jour antérieure à laquelle revenir.", "Non c'è alcun aggiornamento precedente a cui tornare.", "戻れる以前の更新がありません。", "没有可回到的更早更新。", "Não há nenhuma atualização anterior a que voltar.")
_add("r.no_network", "No connection to GitHub and no zip was given: use a zip you already have.", "Sin conexión con GitHub y sin zip indicado: usa un zip que ya tengas.", "Keine Verbindung zu GitHub und kein Zip angegeben: nutze ein vorhandenes Zip.", "Pas de connexion à GitHub et aucun zip indiqué : utilisez un zip que vous avez déjà.", "Nessuna connessione a GitHub e nessuno zip indicato: usa uno zip che hai già.", "GitHub に接続できず、zip も指定されていません。手元の zip を使ってください。", "无法连接 GitHub 且未指定 zip：请使用你已有的 zip。", "Sem ligação ao GitHub e sem zip indicado: use um zip que já tenha.")
_add("p.confirm", "Apply this update? Type yes: ", "¿Aplicar esta actualización? Escribe sí: ", "Dieses Update anwenden? Gib ja ein: ", "Appliquer cette mise à jour ? Tapez oui : ", "Applicare questo aggiornamento? Scrivi sì: ", "この更新を適用しますか？ yes と入力: ", "应用此更新？请输入 yes：", "Aplicar esta atualização? Escreva sim: ")
_add("p.choose", "Choose: ", "Elige: ", "Wähle: ", "Choisissez : ", "Scegli: ", "選択: ", "请选择：", "Escolha: ")
_add("p.version", "Version to update to (empty = latest): ", "Versión de destino (vacío = la última): ", "Zielversion (leer = neueste): ", "Version cible (vide = la dernière) : ", "Versione di destinazione (vuoto = l'ultima): ", "対象バージョン（空 = 最新）: ", "目标版本（留空 = 最新）：", "Versão de destino (vazio = a última): ")
_add("p.zip", "Path of the zip: ", "Ruta del zip: ", "Pfad des Zips: ", "Chemin du zip : ", "Percorso dello zip: ", "zipのパス: ", "zip 路径：", "Caminho do zip: ")
_add("menu.1", "Show the installation", "Ver la instalación", "Installation anzeigen", "Voir l'installation", "Mostra l'installazione", "インストールを表示", "查看安装情况", "Ver a instalação")
_add("menu.2", "List the versions on GitHub", "Listar las versiones de GitHub", "Versionen auf GitHub auflisten", "Lister les versions de GitHub", "Elenca le versioni di GitHub", "GitHub のバージョン一覧", "列出 GitHub 上的版本", "Listar as versões do GitHub")
_add("menu.3", "Plan an update (dry run)", "Planificar una actualización (ensayo)", "Update planen (Probelauf)", "Planifier une mise à jour (essai)", "Pianifica un aggiornamento (prova)", "更新を計画（ドライラン）", "规划更新（试运行）", "Planear uma atualização (ensaio)")
_add("menu.4", "Update now", "Actualizar ahora", "Jetzt aktualisieren", "Mettre à jour maintenant", "Aggiorna ora", "今すぐ更新", "立即更新", "Atualizar agora")
_add("menu.5", "Go back to the previous version", "Volver a la versión anterior", "Zur vorherigen Version zurück", "Revenir à la version précédente", "Torna alla versione precedente", "前のバージョンに戻す", "回到上一个版本", "Voltar à versão anterior")
_add("menu.6", "History of updates", "Historial de actualizaciones", "Update-Verlauf", "Historique des mises à jour", "Cronologia degli aggiornamenti", "更新履歴", "更新历史", "Histórico de atualizações")
_add("menu.0", "Quit", "Salir", "Beenden", "Quitter", "Esci", "終了", "退出", "Sair")
_add("web.listening", "The updater page is at (keep this address private): {url}", "La página del actualizador está en (mantén esta dirección privada): {url}", "Die Updater-Seite ist unter (Adresse privat halten): {url}", "La page de l'outil est à (gardez cette adresse privée) : {url}", "La pagina dell'aggiornatore è su (tieni privato questo indirizzo): {url}", "アップデーターのページ（このアドレスは非公開に）: {url}", "更新程序页面地址（请勿泄露）：{url}", "A página do atualizador está em (mantenha este endereço privado): {url}")
_add("web.stop", "Press Ctrl+C to close the updater.", "Pulsa Ctrl+C para cerrar el actualizador.", "Drücke Strg+C, um den Updater zu schließen.", "Appuyez sur Ctrl+C pour fermer l'outil.", "Premi Ctrl+C per chiudere l'aggiornatore.", "Ctrl+C でアップデーターを閉じます。", "按 Ctrl+C 关闭更新程序。", "Prima Ctrl+C para fechar o atualizador.")
_add("web.working", "Working…", "Trabajando…", "Arbeite…", "En cours…", "In corso…", "処理中…", "处理中…", "A trabalhar…")
_add("web.choose_version", "Choose a version", "Elige una versión", "Version wählen", "Choisissez une version", "Scegli una versione", "バージョンを選択", "选择版本", "Escolha uma versão")
_add("web.confirm_apply", "Apply the update now? A copy is made first and everything goes back by itself if something fails.", "¿Aplicar la actualización ahora? Antes se hace una copia y, si algo falla, todo vuelve solo.", "Update jetzt anwenden? Zuerst wird eine Kopie angelegt; bei einem Fehler geht alles von selbst zurück.", "Appliquer la mise à jour maintenant ? Une copie est faite d'abord et tout revient seul en cas d'échec.", "Applicare l'aggiornamento ora? Prima si fa una copia e, se qualcosa fallisce, tutto torna da solo.", "今すぐ更新しますか？先にコピーを作成し、失敗した場合は自動で元に戻します。", "现在应用更新吗？会先备份，若失败则自动恢复。", "Aplicar a atualização agora? Faz-se primeiro uma cópia e, se algo falhar, tudo volta sozinho.")
_add("tk.unavailable", "Tkinter is not available here; use the page (default) or the text menu (--console).", "Tkinter no está disponible aquí; usa la página (por defecto) o el menú de texto (--console).", "Tkinter ist hier nicht verfügbar; nutze die Seite (Standard) oder das Textmenü (--console).", "Tkinter n'est pas disponible ici ; utilisez la page (par défaut) ou le menu texte (--console).", "Tkinter non è disponibile qui; usa la pagina (predefinita) o il menu di testo (--console).", "ここでは Tkinter を使えません。ページ（既定）またはテキストメニュー（--console）を使ってください。", "此处无法使用 Tkinter；请使用网页（默认）或文本菜单（--console）。", "O Tkinter não está disponível aqui; use a página (por defeito) ou o menu de texto (--console).")


def pick_language(requested=None):
    for raw in (requested, os.environ.get("MONITOR_LANG"), os.environ.get("LC_ALL"), os.environ.get("LANG")):
        code = (raw or "").strip().lower().replace("_", "-")[:2]
        if code == "po":
            code = "pt"
        if code in LANGS:
            return code
    return "en"


_STATE = {"lang": "en"}


def set_language(code):
    _STATE["lang"] = pick_language(code)
    return _STATE["lang"]


def tr(_key, _lang=None, **values):
    """The text of `key` in the language in use (English if a text is missing), with {name} replaced."""
    lang = _lang or _STATE["lang"]
    text = _CAT.get(lang, {}).get(_key) or _CAT["en"].get(_key) or _key
    try:
        return text.format(**values)
    except (KeyError, IndexError, ValueError):
        return text


def notice_text(notice, lang=None):
    texts = notice.get("text") or {}
    return texts.get(lang or _STATE["lang"]) or texts.get("en") or notice.get("id", "")


# ---------------------------------------------------------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------------------------------------------------------
def vkey(text):
    nums = re.findall(r"\d+", str(text or ""))[:4]
    return tuple(int(n) for n in nums) + (0,) * (4 - len(nums))


def now_stamp(now=None):
    return (now or datetime.now(timezone.utc)).strftime("%Y%m%d_%H%M%S")


def iso_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_quiet(command, timeout=60, cwd=None, env=None):
    """subprocess without a shell and without a console window (the flag only exists on Windows)."""
    extra = {"creationflags": 0x08000000} if os.name == "nt" else {}
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env, **extra)


def within(path, folder):
    try:
        Path(path).resolve().relative_to(Path(folder).resolve())
        return True
    except (ValueError, OSError):
        return False


def kind_of(name):
    stem = _VARIANT.sub("", name)
    for kind, pattern in _USER_RE:
        if pattern.match(stem):
            return kind
    return None


def free_mb(path):
    probe = Path(path)
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    return shutil.disk_usage(str(probe)).free // (1024 * 1024)


def writable(path):
    target = Path(path)
    while not target.exists() and target.parent != target:
        target = target.parent
    return os.access(str(target), os.W_OK)


def copy_file(src, dst):
    """Copies atomically (a temporary name in the same folder, then replace) and keeps the permissions."""
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    temp = dst.with_name(f".{dst.name}.upd{secrets.token_hex(3)}")
    try:
        shutil.copyfile(str(src), str(temp))
        shutil.copystat(str(src), str(temp))
        os.replace(str(temp), str(dst))
    finally:
        if temp.exists():
            with contextlib.suppress(OSError):
                temp.unlink()


def move_aside(src, dest_root, relative):
    target = Path(dest_root) / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target = target.with_name(target.name + "." + secrets.token_hex(2))
    shutil.move(str(src), str(target))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def mask(key, value):
    return "***" if SECRET_WORDS.search(key or "") and value not in (None, "", False, True) else value


def private_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        with contextlib.suppress(OSError):
            os.chmod(str(path), 0o700)


# ---------------------------------------------------------------------------------------------------------------------------------------------
# The installation
# ---------------------------------------------------------------------------------------------------------------------------------------------
def find_root(start):
    here = Path(start).resolve()
    for candidate in [here] + list(here.parents):
        if (candidate / "src" / "github_actions_monitor" / "tool_version.py").is_file() or ((candidate / "tool_version.py").is_file() and candidate.parent.name != "src"):
            return candidate
    return None


def read_tool_version(root):
    for path in (Path(root) / "src" / "github_actions_monitor" / "tool_version.py", Path(root) / "tool_version.py"):
        try:
            found = re.search(r'TOOL_VERSION\s*=\s*["\']([^"\']+)["\']', path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if found:
            return found.group(1)
    return None


def folders_of(root, env=None):
    """{config, data, logs, ai}: the same rules as util/paths.py (environment variables, config/paths.json, the data folder as the parent of logs and ai)."""
    env = os.environ if env is None else env
    root = Path(root)
    boot = {}
    chosen = (env.get("MONITOR_PATHS_FILE") or "").strip()
    try:
        data = json.loads((Path(chosen) if chosen else root / "config" / "paths.json").read_text(encoding="utf-8"))
        if isinstance(data, dict):
            boot = {k: v.strip() for k, v in data.items() if k in ("data", "logs", "ai") and isinstance(v, str) and v.strip()}
    except (OSError, ValueError):
        boot = {}
    out = {}
    for kind in ("config", "data", "logs", "ai"):
        value = (env.get(f"MONITOR_{kind.upper()}_DIR") or "").strip()
        if not value and kind != "config":
            value = boot.get(kind, "")
            parent = (env.get("MONITOR_DATA_DIR") or "").strip()
            if not value and parent and kind != "data":
                value = str(Path(parent) / kind)
        path = Path(value) if value else root / kind
        out[kind] = path if path.is_absolute() else root / path
    return out


def config_files(root, folders):
    """[Path] of the configuration files that exist: in config/, next to the launchers (before 1.8.2) and one per account folder."""
    found = []
    for name in CONFIG_NAMES:
        for base in (folders["config"], Path(root)):
            if (base / name).is_file() and (base / name) not in found:
                found.append(base / name)
    accounts = folders["data"] / "accounts"
    if accounts.is_dir():
        for child in sorted(accounts.iterdir())[:200]:
            for name in CONFIG_NAMES:
                if (child / name).is_file():
                    found.append(child / name)
    return found


def load_json_strict(path):
    """(data, duplicate keys, error): the duplicate keys of an object are found, the last one wins like in the monitor."""
    duplicates = []

    def hook(pairs):
        seen = {}
        for key, value in pairs:
            if key in seen:
                duplicates.append(key)
            seen[key] = value
        return seen

    try:
        text = Path(path).read_text(encoding="utf-8-sig")
        return json.loads(text, object_pairs_hook=hook), duplicates, None
    except (OSError, ValueError) as error:
        return None, duplicates, str(error)[:120]


def probe_port(port, timeout=1.0):
    """{"open", "ours", "version"}: whether something listens on 127.0.0.1:port and whether it answers like the monitor."""
    info = {"port": port, "open": False, "ours": False, "version": None}
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            info["open"] = True
    except OSError:
        return info
    try:
        request = urllib.request.Request(f"http://127.0.0.1:{port}/api/health", headers={"User-Agent": UA})
        with urllib.request.urlopen(request, timeout=timeout + 1) as reply:
            data = json.loads(reply.read(65536).decode("utf-8", "replace"))
        if isinstance(data, dict):
            info["version"] = str(data.get("version") or data.get("tool_version") or "") or None
            info["ours"] = "version" in data or "tool_version" in data or "status" in data or "ok" in data or "loaded" in data
    except urllib.error.HTTPError as error:
        info["ours"] = error.code in (401, 403)            # a monitor in the team mode refuses an anonymous reader
    except (OSError, ValueError):
        pass
    return info


def in_container(env=None):
    env = os.environ if env is None else env
    if env.get("MONITOR_IN_CONTAINER") == "1":
        return True
    if os.name == "nt":
        return False
    if Path("/.dockerenv").exists() or Path("/run/.containerenv").exists():
        return True
    with contextlib.suppress(OSError):
        text = Path("/proc/1/cgroup").read_text(encoding="utf-8", errors="replace")
        return any(word in text for word in ("docker", "containerd", "kubepods"))
    return False


def under_service(env=None):
    env = os.environ if env is None else env
    return bool(env.get("INVOCATION_ID") or env.get("JOURNAL_STREAM") or Path("/etc/systemd/system/github-actions-monitor.service").exists())


def ports_of(cfg):
    ports = {"complete": 8765, "lite": 8766}
    node = (cfg or {}).get("ports") if isinstance(cfg, dict) else None
    if isinstance(node, dict):
        for key in ports:
            if isinstance(node.get(key), int) and 1 <= node[key] <= 65535:
                ports[key] = node[key]
    return ports


def detect(root, env=None, probe=None, probing=True):
    """What is installed in `root`: version, layout, editions with a configuration, folders, ports and whether it runs."""
    probe = probe or probe_port
    root = Path(root)
    env = os.environ if env is None else env
    version = read_tool_version(root)
    folders = folders_of(root, env)
    configs = config_files(root, folders)
    editions = []
    cfg_main = None
    for path in configs:
        if "accounts" in path.parts:
            continue
        edition = "lite" if path.name == "actions_monitor_lite.json" else "complete"
        if edition not in editions:
            editions.append(edition)
        if cfg_main is None and edition == "complete":
            cfg_main = load_json_strict(path)[0]
    if not editions:
        editions = ["complete"]
    ports = ports_of(cfg_main)
    running = {}
    if probing:
        for edition in editions:
            running[edition] = probe(ports[edition])
    layout = "tree" if (root / "src" / "github_actions_monitor").is_dir() else "flat"
    mode = "docker" if in_container(env) else ("service" if under_service(env) else "folder")
    return {"root": str(root), "version": version, "layout": layout, "editions": editions, "folders": {k: str(v) for k, v in folders.items()},
            "configs": [str(p) for p in configs], "ports": ports, "running": running, "mode": mode,
            "has_data": any(folders["data"].glob("*")) if folders["data"].is_dir() else False}


# ---------------------------------------------------------------------------------------------------------------------------------------------
# GitHub (or a zip you already have)
# ---------------------------------------------------------------------------------------------------------------------------------------------
def release_from_api(item):
    tag = str(item.get("tag_name") or "")
    assets = {}
    for asset in item.get("assets") or []:
        assets[asset.get("name", "")] = {"url": asset.get("browser_download_url", ""), "size": int(asset.get("size") or 0)}
    return {"tag": tag, "version": tag.lstrip("vV"), "name": item.get("name") or tag, "published": item.get("published_at") or "", "body": item.get("body") or "",
            "prerelease": bool(item.get("prerelease")), "draft": bool(item.get("draft")), "assets": assets}


def parse_sums(text, name=ZIP_NAME):
    """The SHA-256 of `name` in the text of a SHA256SUMS file, or None."""
    for line in (text or "").splitlines():
        found = re.match(r"^\s*([0-9a-fA-F]{64})\s+\*?(.+?)\s*$", line)
        if found and Path(found.group(2).replace("\\", "/")).name == name:
            return found.group(1).lower()
    return None


def host_ok(url):
    found = re.match(r"^https://([^/:]+)(?::443)?/", url or "")
    if not found:
        return False
    host = found.group(1).lower()
    return any(host == allowed or host.endswith("." + allowed) for allowed in DOWNLOAD_HOSTS)


class GitHubSource:
    """Lists the releases of the repository (the `gh` tool if it is there and logged in, else the public API with a plain User-Agent) and downloads the zip and its SHA256SUMS."""
    kind = "github"

    def __init__(self, repo=REPO, prefer_gh=True, timeout=30):
        self.repo, self.prefer_gh, self.timeout = repo, prefer_gh, timeout

    def _page(self, page):
        path = f"repos/{self.repo}/releases?per_page=100&page={page}"
        if self.prefer_gh and shutil.which("gh"):
            with contextlib.suppress(OSError, subprocess.SubprocessError, ValueError):
                done = run_quiet(["gh", "api", path], timeout=self.timeout * 2)
                if done.returncode == 0:
                    return json.loads(done.stdout)
        request = urllib.request.Request("https://api.github.com/" + path, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(request, timeout=self.timeout) as reply:
            return json.loads(reply.read(8 << 20).decode("utf-8", "replace"))

    def releases(self):
        out = []
        try:
            for page in range(1, 6):
                batch = self._page(page)
                out.extend(release_from_api(item) for item in batch if isinstance(item, dict))
                if len(batch) < 100:
                    break
        except (OSError, ValueError) as error:
            raise UpdaterError(OFFLINE, "no connection to GitHub: " + str(error)[:100], "r.no_network")
        out = [r for r in out if not r["draft"] and re.match(r"^\d+(\.\d+){1,3}$", r["version"])]
        return sorted(out, key=lambda r: vkey(r["version"]), reverse=True)

    def _download(self, url, dest, limit):
        if not host_ok(url):
            raise UpdaterError(FETCH_FAILED, "download address not allowed: " + url[:80])
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        size = 0
        with urllib.request.urlopen(request, timeout=self.timeout) as reply, open(dest, "wb") as out:
            if not host_ok(reply.geturl()):
                raise UpdaterError(FETCH_FAILED, "redirect to a host that is not allowed")
            for block in iter(lambda: reply.read(1 << 20), b""):
                size += len(block)
                if size > limit:
                    raise UpdaterError(FETCH_FAILED, "download larger than allowed")
                out.write(block)

    def fetch_zip(self, release, dest_dir):
        """(zip path, expected SHA-256 or None, how it was verified)."""
        assets = release.get("assets") or {}
        if ZIP_NAME not in assets:
            raise UpdaterError(FETCH_FAILED, f"{release.get('tag')} has no {ZIP_NAME}")
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        zip_path = Path(dest_dir) / ZIP_NAME
        expected = None
        if SUMS_NAME in assets:
            sums = Path(dest_dir) / SUMS_NAME
            try:
                self._download(assets[SUMS_NAME]["url"], sums, 1 << 20)
            except (OSError, urllib.error.URLError) as error:
                raise UpdaterError(FETCH_FAILED, "could not download SHA256SUMS: " + str(error)[:80])
            expected = parse_sums(sums.read_text(encoding="utf-8", errors="replace"))
        if expected is None:
            raise UpdaterError(FETCH_FAILED, f"{release.get('tag')} publishes no SHA-256 for the zip", "c.unverified")
        if not (zip_path.is_file() and sha256_file(zip_path) == expected):
            try:
                self._download(assets[ZIP_NAME]["url"], zip_path, MAX_ZIP)
            except (OSError, urllib.error.URLError) as error:
                raise UpdaterError(FETCH_FAILED, "could not download the zip: " + str(error)[:80])
        return zip_path, expected, "sums"


class LocalZipSource:
    """A zip you already have (no connection needed). The SHA-256 is checked when you give it (--sha256) or when a SHA256SUMS sits next to the zip."""
    kind = "zip"

    def __init__(self, path, sha256=None):
        self.path, self.sha256 = Path(path), (sha256 or "").strip().lower() or None

    def releases(self):
        version = None
        try:
            with zipfile.ZipFile(self.path) as zf:
                for info in zf.infolist():
                    if info.filename.endswith("src/github_actions_monitor/tool_version.py") and info.file_size < 4096:
                        found = re.search(r'TOOL_VERSION\s*=\s*"([^"]+)"', zf.read(info).decode("utf-8", "replace"))
                        version = found.group(1) if found else None
                        break
        except (OSError, zipfile.BadZipFile) as error:
            raise UpdaterError(FETCH_FAILED, f"{self.path} is not a usable zip: {error}")
        if not version:
            raise UpdaterError(FETCH_FAILED, f"{self.path} is not a zip of the monitor")
        return [{"tag": "v" + version, "version": version, "name": self.path.name, "published": "", "body": "", "prerelease": False, "draft": False, "assets": {}}]

    def fetch_zip(self, release, dest_dir):
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        zip_path = Path(dest_dir) / ZIP_NAME
        shutil.copyfile(str(self.path), str(zip_path))
        expected = self.sha256
        how = "given" if expected else None
        if expected is None:
            sibling = self.path.with_name(SUMS_NAME)
            if sibling.is_file():
                expected = parse_sums(sibling.read_text(encoding="utf-8", errors="replace"), self.path.name) or parse_sums(sibling.read_text(encoding="utf-8", errors="replace"))
                how = "sums" if expected else None
        return zip_path, expected, how


# ---------------------------------------------------------------------------------------------------------------------------------------------
# The zip: checked before anything is unpacked, unpacked into a new folder, never executed
# ---------------------------------------------------------------------------------------------------------------------------------------------
def check_zip_members(zf):
    """Raises UpdaterError for an unsafe zip. Returns (top folder name, [infos of files])."""
    infos = zf.infolist()
    if len(infos) > MAX_FILES:
        raise UpdaterError(FETCH_FAILED, "too many files in the zip")
    total = 0
    tops = set()
    files = []
    for info in infos:
        name = info.filename
        norm = name.replace("\\", "/")
        parts = [p for p in norm.split("/") if p]
        if (not parts or norm.startswith("/") or re.match(r"^[A-Za-z]:", norm) or ".." in parts or "\x00" in name or any(p.strip() != p or p.endswith(".") for p in parts)):
            raise UpdaterError(FETCH_FAILED, "unsafe path in the zip: " + repr(name)[:80])
        mode = (info.external_attr >> 16) & 0xFFFF
        if mode and stat.S_ISLNK(mode):
            raise UpdaterError(FETCH_FAILED, "the zip holds a symbolic link: " + name[:80])
        if mode and (stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode)):
            raise UpdaterError(FETCH_FAILED, "the zip holds a special file: " + name[:80])
        tops.add(parts[0])
        if info.is_dir():
            continue
        total += info.file_size
        if info.file_size > 1024 * 1024 and info.compress_size and info.file_size / info.compress_size > MAX_RATIO:
            raise UpdaterError(FETCH_FAILED, "suspicious compression ratio: " + name[:80])
        files.append(info)
    if total > MAX_UNPACKED:
        raise UpdaterError(FETCH_FAILED, "the zip unpacks to more than allowed")
    if len(tops) != 1:
        raise UpdaterError(FETCH_FAILED, "the zip must hold one top folder")
    return tops.pop(), files


def extract_zip(zip_path, dest):
    """Unpacks into `dest` (new, empty) writing each file by hand under a path that is checked; returns the product folder."""
    dest = Path(dest)
    if dest.exists() and any(dest.iterdir()):
        raise UpdaterError(FETCH_FAILED, "the folder to unpack into is not empty")
    dest.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            top, files = check_zip_members(zf)
            for info in files:
                target = (dest / info.filename.replace("\\", "/")).resolve()
                if not within(target, dest):
                    raise UpdaterError(FETCH_FAILED, "a path leaves the folder: " + info.filename[:80])
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as source, open(target, "wb") as out:
                    shutil.copyfileobj(source, out, 1 << 20)
                mode = (info.external_attr >> 16) & 0o777
                if os.name != "nt" and mode:
                    os.chmod(str(target), (mode | 0o600) & 0o755)
    except zipfile.BadZipFile as error:
        raise UpdaterError(FETCH_FAILED, "damaged zip: " + str(error)[:80])
    product = dest / top
    if read_tool_version(product) is None or not (product / "src" / "github_actions_monitor").is_dir():
        raise UpdaterError(FETCH_FAILED, "the zip is not a package of the monitor")
    return product


# ---------------------------------------------------------------------------------------------------------------------------------------------
# The registry of migrations
# ---------------------------------------------------------------------------------------------------------------------------------------------
EMBEDDED_REGISTRY = None  # filled in the published copy of this file by tools/make_release.py (the registry of every release up to the one it ships with)


def _digest(view):
    """The SHA-256 of a schema, with the end anchor of the patterns written one way ($ against a backslash Z is the same rule); the generator of the registry does the same."""
    flat = {}
    for key, entry in view.items():
        entry = dict(entry)
        bounds = entry.get("bounds")
        if isinstance(bounds, dict) and "re" in bounds:
            entry["bounds"] = {"re": bounds["re"].replace(chr(92) + "Z", "$")}
        flat[key] = entry
    return hashlib.sha256(json.dumps(flat, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class Registry:
    def __init__(self, docs=None, launchers=None):
        self.docs = dict(docs or {})
        self.launchers = launchers or {"files": {}, "versions": {}}

    @classmethod
    def from_dir(cls, folder):
        docs, launchers = {}, None
        folder = Path(folder)
        if folder.is_dir():
            for path in sorted(folder.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if path.name == "launchers.json":
                    launchers = data
                elif isinstance(data, dict) and data.get("version") and path.stem == data["version"]:
                    docs[data["version"]] = data
        return cls(docs, launchers)

    @classmethod
    def embedded(cls):
        if not EMBEDDED_REGISTRY:
            return cls()
        return cls(EMBEDDED_REGISTRY.get("docs"), EMBEDDED_REGISTRY.get("launchers"))

    def merged(self, other):
        """The union; what is already here wins over `other`."""
        docs = dict(other.docs)
        docs.update(self.docs)
        files = dict(other.launchers.get("files", {}))
        files.update(self.launchers.get("files", {}))
        versions = dict(other.launchers.get("versions", {}))
        versions.update(self.launchers.get("versions", {}))
        return Registry(docs, {"files": files, "versions": versions})

    def versions(self):
        return sorted(self.docs, key=vkey)

    def chain(self, frm, to):
        return [self.docs[v] for v in self.versions() if vkey(frm) < vkey(v) <= vkey(to)]

    def schema_at(self, version):
        """{key: {kind, bounds, default}} of a version, rebuilt from the first snapshot and the differences (None when the registry cannot say)."""
        view = None
        for v in self.versions():
            if vkey(v) > vkey(version):
                break
            doc = self.docs[v]
            if view is None:
                view = json.loads(json.dumps(doc["snapshot"])) if doc.get("snapshot") else None
                if view is None:
                    continue
            settings = doc.get("settings") or {}
            for item in settings.get("added", []):
                view[item["key"]] = {k: val for k, val in item.items() if k != "key"}
            for item in settings.get("removed", []):
                view.pop(item["key"], None)
            for item in settings.get("changed", []):
                entry = view.setdefault(item["key"], {})
                entry.update(item.get("new") or {})
        return view

    def check(self):
        """[problem]: the rebuilt schema of every version must have the digest the file declares."""
        problems = []
        for v in self.versions():
            view = self.schema_at(v)
            if view is None or _digest(view) != self.docs[v].get("digest"):
                problems.append(v)
        return problems

    def gaps(self, frm, to, published):
        return [v for v in published if vkey(frm) < vkey(v) <= vkey(to) and v not in self.docs]

    def requires(self, frm, to):
        need = []
        for doc in self.chain(frm, to):
            minimum = ((doc.get("manual") or {}).get("requires") or {}).get("from_at_least")
            if minimum and vkey(frm) < vkey(minimum):
                need.append(minimum)
        return need


def load_registry(extracted_product=None, installed_root=None):
    reg = Registry()
    if extracted_product:
        reg = reg.merged(Registry.from_dir(Path(extracted_product) / "assets" / "migrations"))
    reg = reg.merged(Registry.embedded())
    if installed_root:
        reg = reg.merged(Registry.from_dir(Path(installed_root) / "assets" / "migrations"))
    here = Path(__file__).resolve().parent
    for candidate in (here / "assets" / "migrations", here.parent / "assets" / "migrations"):
        reg = reg.merged(Registry.from_dir(candidate))
    return reg


# ---------------------------------------------------------------------------------------------------------------------------------------------
# The configuration: migration and coherence
# ---------------------------------------------------------------------------------------------------------------------------------------------
def _has(tree, dotted):
    node = tree
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def _get(tree, dotted, default=None):
    node = tree
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def _set(tree, dotted, value):
    node = tree
    parts = dotted.split(".")
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value


def _del(tree, dotted):
    parts = dotted.split(".")
    chain = [tree]
    for part in parts[:-1]:
        if not isinstance(chain[-1], dict) or part not in chain[-1]:
            return
        chain.append(chain[-1][part])
    if isinstance(chain[-1], dict):
        chain[-1].pop(parts[-1], None)
    for index in range(len(parts) - 1, 0, -1):          # a parent that became empty by this removal goes too
        parent = chain[index - 1]
        if isinstance(chain[index], dict) and not chain[index]:
            parent.pop(parts[index - 1], None)


def _unset(value):
    return value is None


def migrate_config(cfg, docs, policy="conservative"):
    """(new configuration, changes, notices) for a chain of registry documents. `policy`: conservative (keep what you set, new defaults for what you never set),
    keep_old (also write the old default where you set nothing) or adopt_new (also move the values that still hold the old default)."""
    out = json.loads(json.dumps(cfg))
    changes, notices = [], []

    def default_change(key, old, new, version, notice=None, absent_or_null=False):
        explicit = _has(out, key) and (not absent_or_null or not _unset(_get(out, key)))
        entry = {"key": key, "version": version, "old": mask(key, old), "new": mask(key, new)}
        if explicit:
            value = _get(out, key)
            if value == old and policy == "adopt_new":
                _set(out, key, new)
                entry["type"] = "adopted"
            elif value == old:
                entry["type"] = "kept"
            else:
                return
        else:
            if policy == "keep_old":
                _set(out, key, old)
                entry["type"] = "pinned"
            else:
                entry["type"] = "new_default"
        if notice:
            entry["notice"] = notice["id"]
            notices.append({"id": notice["id"], "level": notice.get("level", "info"), "version": version, "keys": notice.get("keys", []), "text": notice.get("text", {}), "effect": entry["type"]})
        changes.append(entry)

    for doc in docs:
        version = doc["version"]
        manual = doc.get("manual") or {}
        renamed_from = set()
        for item in manual.get("renamed", []):
            old, new = item["from"], item["to"]
            renamed_from.add(old)
            if _has(out, old):
                value = _get(out, old)
                _del(out, old)
                if not _has(out, new):
                    _set(out, new, value)
                changes.append({"type": "renamed", "key": old, "new_key": new, "version": version})
        for item in (doc.get("settings") or {}).get("removed", []):
            key = item["key"]
            if key not in renamed_from and _has(out, key):
                changes.append({"type": "removed", "key": key, "version": version, "old": mask(key, _get(out, key))})
                _del(out, key)
        pending = manual.get("notices", [])
        covered = {n["keys"][0] for n in pending if "old_value" in n and n.get("keys")}
        for item in (doc.get("settings") or {}).get("changed", []):
            old, new = item.get("old") or {}, item.get("new") or {}
            if "default" in old and "default" in new and old["default"] != new["default"] and item["key"] not in covered:
                default_change(item["key"], old["default"], new["default"], version)
        for notice in pending:
            when = notice.get("when") or {}
            if "old_value" in notice and notice.get("keys"):
                default_change(notice["keys"][0], notice["old_value"], notice["new_value"], version, notice, absent_or_null="absent_or_null" in when)
            else:
                applies = True
                if "present" in when:
                    applies = _has(cfg, when["present"])
                if applies:
                    notices.append({"id": notice["id"], "level": notice.get("level", "info"), "version": version, "keys": notice.get("keys", []), "text": notice.get("text", {}), "effect": "info"})
    return out, changes, notices


def check_value(entry, value):
    """None when `value` suits the schema entry, else (code, params)."""
    kind, bounds = entry.get("kind"), entry.get("bounds")
    if kind == "bool":
        return None if isinstance(value, bool) else ("type", {"kind": "bool"})
    if kind in ("int", "float"):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or (kind == "int" and isinstance(value, float) and not value.is_integer()):
            return ("type", {"kind": kind})
        if isinstance(bounds, list) and len(bounds) == 2 and not (bounds[0] <= value <= bounds[1]):
            return ("range", {"value": value, "rule": f"{bounds[0]}..{bounds[1]}"})
    if kind == "enum" and isinstance(bounds, list):
        return None if value in bounds else ("range", {"value": value, "rule": "|".join(str(b) for b in bounds)[:80]})
    if kind == "text":
        if not isinstance(value, str):
            return ("type", {"kind": "text"})
        if isinstance(bounds, dict) and "re" in bounds:
            with contextlib.suppress(re.error):
                if not re.search(bounds["re"], value):
                    return ("range", {"value": value[:30], "rule": "pattern"})
    return None


def check_config(cfg, schema, version_label):
    """Incoherences of a configuration against a schema ({key: entry}); [] when it fits. Each: (code, severity, params)."""
    issues = []
    if not schema:
        return issues
    known_prefixes = set()
    for key in schema:
        parts = key.split(".")
        for index in range(1, len(parts)):
            known_prefixes.add(".".join(parts[:index]))

    def walk(node, prefix):
        for key, value in node.items():
            path = prefix + key
            if key.startswith("_"):
                continue
            if path in schema:
                problem = check_value(schema[path], value)
                if problem:
                    issues.append((problem[0], "warn", dict(problem[1], key=path, to=version_label)))
            elif isinstance(value, dict) and (path in known_prefixes or any(k.startswith(path + ".") for k in schema)):
                walk(value, path + ".")
            elif path in known_prefixes:
                continue
            else:
                issues.append(("unknown_key", "warn", {"key": path, "to": version_label}))
    if isinstance(cfg, dict):
        walk(cfg, "")
    for path, entry in schema.items():
        if entry.get("kind") == "path" and _has(cfg, path):
            value = _get(cfg, path)
            if isinstance(value, str) and value and os.path.isabs(value) and not os.path.exists(value):
                issues.append(("path", "warn", {"key": path, "path": value}))
    return issues


def dump_config(path, cfg):
    """Writes the configuration in the style of the file it replaces (indentation, line ends) and atomically."""
    path = Path(path)
    indent = 2
    newline = "\n"
    try:
        raw = path.read_bytes().decode("utf-8-sig")
        newline = "\r\n" if "\r\n" in raw else "\n"
        found = re.search(r"\n([ \t]+)\"", raw)
        if found:
            indent = "\t" if found.group(1).startswith("\t") else len(found.group(1))
    except OSError:
        pass
    text = json.dumps(cfg, indent=indent, ensure_ascii=False) + "\n"
    temp = path.with_name(f".{path.name}.upd{secrets.token_hex(3)}")
    temp.write_bytes(text.replace("\n", newline).encode("utf-8"))
    with contextlib.suppress(OSError):
        shutil.copystat(str(path), str(temp))
    os.replace(str(temp), str(path))


# ---------------------------------------------------------------------------------------------------------------------------------------------
# The launchers: what a person changed in theirs
# ---------------------------------------------------------------------------------------------------------------------------------------------
def _lines(text):
    return text.replace("\r\n", "\n").split("\n")


def merge_launcher(pristine_old, installed, shipped_new):
    """(text for the new launcher, method). Re-applies the lines the person added or changed (found by comparing the installed launcher with the shipped text of its version) to the new shipped launcher.
    method: "same" nothing of theirs; "merged" their lines are back; "saved" they could not be placed (the caller keeps their file next to the new one)."""
    old_l, inst_l, new_l = _lines(pristine_old), _lines(installed), _lines(shipped_new)
    if old_l == inst_l:
        return shipped_new, "same"
    result = list(new_l)
    cursor = 0
    ops = [op for op in difflib.SequenceMatcher(None, old_l, inst_l, autojunk=False).get_opcodes() if op[0] != "equal"]
    for tag, i1, i2, j1, j2 in ops:
        mine = inst_l[j1:j2]
        removed = old_l[i1:i2]
        if tag in ("replace", "delete") and removed:
            index = next((k for k in range(len(result) - len(removed) + 1) if result[k:k + len(removed)] == removed), None)
            if index is None:
                return shipped_new, "saved"
            result[index:index + len(removed)] = mine
            cursor = index + len(mine)
        else:
            anchor = next((line for line in reversed(old_l[:i1]) if line.strip() and line in result), None)
            if i1 == 0 or anchor is None:
                position = 0 if i1 == 0 else None
            else:
                position = next((k + 1 for k in range(cursor, len(result)) if result[k] == anchor), None)
            if position is None:
                return shipped_new, "saved"
            result[position:position] = mine
            cursor = position + len(mine)
    return "\n".join(result), "merged"


def eol_of(data):
    return "\r\n" if b"\r\n" in data else "\n"


# ---------------------------------------------------------------------------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------------------------------------------------------------------------
STEPS = ("lock", "download", "extract", "backup", "copy", "retire", "launchers", "config", "layout", "verify", "start")
LAUNCHER_RE = re.compile(r"^[^/\\]+\.(bat|sh|command)$")


def is_product_name(name):
    return name in PRODUCT_ROOT_NAMES or (name.endswith(PRODUCT_ROOT_SUFFIXES) and kind_of(name) is None and not name.endswith(".json"))


def classify_member(rel):
    """The area of a path of the zip (relative to its top folder): "product", or None when an update must not write it."""
    parts = Path(rel).parts
    if not parts:
        return None
    if len(parts) == 1:
        return "product" if is_product_name(parts[0]) else None
    if parts[0] in PRODUCT_DIRS and not any(p in EXCLUDE_DIRS for p in parts):
        return "product"
    return None


def inventory(root, folders):
    """[(area, relative posix path, absolute Path)] of everything an update must be able to bring back: the product, the configuration, the data, the AI folder and the loose files of an old flat layout."""
    root = Path(root)
    found = []
    for child in sorted(root.iterdir()) if root.is_dir() else []:
        if child.is_file():
            if is_product_name(child.name):
                found.append(("product", child.name, child))
            elif child.suffix in (".json", ".jsonl", ".sqlite3") or kind_of(child.name):
                found.append(("rootuser", child.name, child))
    for name in PRODUCT_DIRS:
        base = root / name
        if base.is_dir():
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
                for filename in filenames:
                    path = Path(dirpath) / filename
                    if path.is_symlink() or filename.endswith((".pyc", ".pyo")):
                        continue
                    found.append(("product", path.relative_to(root).as_posix(), path))
    for area in ("config", "data", "ai"):
        base = Path(folders[area])
        if base.is_dir() and not (area == "data" and base.resolve() == root.resolve()):
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith("layout_backup_")]
                for filename in filenames:
                    path = Path(dirpath) / filename
                    if path.is_symlink() or filename.endswith(".tmp") or ".upd" in filename:
                        continue
                    found.append((area, path.relative_to(base).as_posix(), path))
    return found


def base_of(area, root, folders):
    return Path(root) if area in ("product", "rootuser") else Path(folders[area])


def data_schema_of(folders):
    """The highest schema number of the SQLite databases found in the data folder (0 when there is none)."""
    import sqlite3
    best = 0
    base = Path(folders["data"])
    if not base.is_dir():
        return 0
    for path in list(base.rglob("storage.sqlite3"))[:50]:
        try:
            conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=2.0)
            try:
                row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
                best = max(best, int(row[0]) if row else 0)
            finally:
                conn.close()
        except (sqlite3.Error, ValueError, OSError):
            continue
    return best


def resolve_launchers(read_old, product, registry, installed_version):
    """[{"name", "state", "data"}] for each launcher the new product ships. state: new (the person had none), same, merged (their lines are back in `data`), saved (could not place them: `custom` holds their file), unknown (cannot tell what is theirs: `custom`)."""
    out = []
    for path in sorted(Path(product).glob("*")):
        if not (path.is_file() and LAUNCHER_RE.match(path.name)):
            continue
        shipped = path.read_bytes()
        old = read_old(path.name)
        entry = {"name": path.name, "state": "new", "data": shipped, "custom": None}
        if old is not None:
            installed_text = old.decode("utf-8", "replace").replace("\r\n", "\n")
            sha = (registry.launchers.get("versions", {}).get(installed_version or "", {})).get(path.name)
            pristine = registry.launchers.get("files", {}).get(sha) if sha else None
            if pristine is None and any(installed_text == t for t in registry.launchers.get("files", {}).values()):
                entry["state"] = "same"
            elif pristine is None:
                entry["state"], entry["custom"] = "unknown", old
            else:
                merged, how = merge_launcher(pristine, installed_text, shipped.decode("utf-8", "replace").replace("\r\n", "\n"))
                if how == "same":
                    entry["state"] = "same"
                elif how == "merged":
                    entry["state"] = "merged"
                    entry["data"] = merged.replace("\n", eol_of(shipped)).encode("utf-8")
                else:
                    entry["state"], entry["custom"] = "saved", old
        out.append(entry)
    return out


class Updater:
    def __init__(self, root, source=None, backups=None, env=None, emit=None, probe=None, lang=None):
        self.root = Path(root).resolve()
        self.source = source or GitHubSource()
        self.env = dict(os.environ if env is None else env)
        self.backups = Path(backups or self.env.get("MONITOR_UPDATE_BACKUPS") or self.root / BACKUPS_NAME).resolve()
        self.emit_cb = emit
        self.probe = probe or (lambda port: probe_port(port))
        self._releases = None
        self._staged = {}
        if lang:
            set_language(lang)

    # --- events
    def emit(self, step, status, detail=""):
        if self.emit_cb:
            self.emit_cb({"step": step, "status": status, "detail": detail, "at": iso_now()})

    # --- detection and versions
    def detect(self, probing=True):
        return detect(self.root, self.env, self.probe, probing)

    def folders(self):
        return folders_of(self.root, self.env)

    def releases(self, refresh=False):
        if self._releases is None or refresh:
            self._releases = self.source.releases()
        return self._releases

    def annotate(self, releases=None, installed=None):
        installed = installed or read_tool_version(self.root)
        out = []
        newest = None
        for r in (releases if releases is not None else self.releases()):
            if not r.get("prerelease") and newest is None:
                newest = r["version"]
            relation = "current" if installed and vkey(r["version"]) == vkey(installed) else ("newer" if installed and vkey(r["version"]) > vkey(installed) else "older")
            out.append(dict(r, relation=relation, latest=(r["version"] == newest and not r.get("prerelease"))))
        return out

    def resolve_target(self, target):
        rels = self.releases()
        if not target or str(target).lower() == "latest":
            stable = [r for r in rels if not r.get("prerelease")] or rels
            if not stable:
                raise UpdaterError(USAGE, "no version found")
            return stable[0]
        wanted = str(target).lstrip("vV")
        for r in rels:
            if vkey(r["version"]) == vkey(wanted) and r["version"].count(".") == wanted.count("."):
                return r
        for r in rels:
            if vkey(r["version"]) == vkey(wanted):
                return r
        raise UpdaterError(USAGE, f"version {target} is not among the published ones")

    # --- download, verify, unpack
    def prepare(self, release):
        cache = self.backups / "downloads" / release["version"]
        zip_path, expected, how = self.source.fetch_zip(release, cache)
        actual = sha256_file(zip_path)
        return {"zip": zip_path, "expected": expected, "actual": actual, "sha_ok": expected is None or expected == actual, "verified": how if expected else None, "size": zip_path.stat().st_size}

    def unpack(self, prep, release):
        key = release["version"]
        if key in self._staged and Path(self._staged[key]).is_dir():
            return Path(self._staged[key])
        stage = self.backups / "_staging" / f"{key}_{secrets.token_hex(3)}"
        private_dir(self.backups)
        product = extract_zip(prep["zip"], stage)
        self._staged[key] = product
        return product

    def cleanup(self):
        for product in list(self._staged.values()):
            stage = Path(product).parent
            if within(stage, self.backups / "_staging"):
                shutil.rmtree(str(stage), ignore_errors=True)
        self._staged.clear()
        with contextlib.suppress(OSError):
            (self.backups / "_staging").rmdir()

    # --- pending work
    def pending(self):
        if not self.backups.is_dir():
            return None
        for folder in sorted(self.backups.iterdir()):
            journal = folder / "journal.json"
            if folder.is_dir() and journal.is_file():
                try:
                    data = json.loads(journal.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if data.get("status") in ("applying", "rolling_back"):
                    return folder
        return None

    def lock_state(self):
        lock = self.backups / ".lock"
        if not lock.is_file():
            return None
        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if time.time() - float(data.get("time") or 0) > 7200:
            return None
        return data

    # --- the plan
    def plan(self, target=None, options=None):
        opts = dict(options or {})
        policy = opts.get("policy", "conservative")
        inst = self.detect()
        installed = inst["version"] or "0"
        release = self.resolve_target(target)
        to = release["version"]
        direction = "same" if vkey(to) == vkey(installed) else ("upgrade" if vkey(to) > vkey(installed) else "downgrade")
        checks = []

        def add(code, severity, **params):
            checks.append({"code": code, "severity": severity, "params": params, "text": tr("c." + code, **params)})

        prep = self.prepare(release)
        product = None
        if not prep["sha_ok"]:
            add("sha", "block")
        else:
            if prep["verified"] is None:
                add("unverified", "warn")
            product = self.unpack(prep, release)
        registry = load_registry(product, self.root)
        lang = _STATE["lang"]
        if direction == "same":
            add("same_vm", "info", version=to)
        if inst["mode"] == "docker" and not opts.get("allow_container"):
            add("container", "block")
        if self.pending():
            add("pending", "block", backup=self.pending().name)
        if self.lock_state():
            add("locked", "block")
        for edition, state in inst["running"].items():
            if state.get("open"):
                if state.get("ours"):
                    if opts.get("handover"):
                        add("handover", "info", port=state["port"])       # the monitor that asks for the update stops by itself (see handover_wait)
                    else:
                        add("running", "block", port=state["port"])
                else:
                    add("port", "warn", port=state["port"])
        if direction == "downgrade":
            add("downgrade", "warn" if opts.get("allow_downgrade") else "block", **{"from_": installed, "to": to})
        published = [r["version"] for r in self.releases()] if getattr(self.source, "kind", "") == "github" else []
        gaps = registry.gaps(installed, to, published) if direction == "upgrade" else []
        if gaps:
            add("registry_gap", "warn", versions=", ".join(sorted(gaps, key=vkey)))
        for need in (registry.requires(installed, to) if direction == "upgrade" else []):
            add("required", "block", need=need)
        folders = self.folders()
        schema_to = registry.schema_at(to)
        if product is not None:
            for edition in inst["editions"]:
                launcher = "MONITOR_LITE_GITHUB_ACTIONS.sh" if edition == "lite" else "MONITOR_GITHUB_ACTIONS.sh"
                if not (Path(product) / launcher).is_file():
                    add("edition", "block", edition=edition)
        have = data_schema_of(folders)
        want = (registry.docs.get(to) or {}).get("data_schema")
        if direction == "downgrade" and want and have > want:
            add("db_newer", "block", have=have, want=want)
        # disk and permissions
        snapshot_mb = sum(p.stat().st_size for _a, _r, p in inventory(self.root, folders) if p.exists()) // (1024 * 1024) + 1
        need = int((snapshot_mb + 3 * (prep["size"] // (1024 * 1024) + 1)) * 1.2) + 5
        for where in {str(self.backups), str(self.root)}:
            if free_mb(where) < need:
                add("disk", "block", need=need, free=free_mb(where), where=where)
            if not writable(where):
                add("perm", "block", where=where)
        # configuration
        config_plan, notices = [], {}
        docs = registry.chain(installed, to) if direction == "upgrade" else []
        for path in [Path(p) for p in inst["configs"]]:
            data, duplicates, error = load_json_strict(path)
            entry = {"file": str(path), "changes": [], "issues": []}
            if error:
                add("badjson", "warn", file=path.name, error=error)
                config_plan.append(entry)
                continue
            for key in sorted(set(duplicates)):
                add("dup", "warn", key=key, file=path.name)
            migrated, changes, notes = (migrate_config(data, docs, policy) if docs else (data, [], []))
            entry["changes"] = changes
            for code, severity, params in check_config(migrated, schema_to, to):
                add(code, severity, **params)
                entry["issues"].append(code)
            for note in notes:
                notices[note["id"]] = note
            config_plan.append(entry)
        # launchers
        launchers = []
        if product is not None:
            def read_old(name):
                p = self.root / name
                return p.read_bytes() if p.is_file() else None
            for item in resolve_launchers(read_old, product, registry, installed):
                launchers.append({"name": item["name"], "state": item["state"]})
                if item["state"] in ("merged", "saved", "unknown"):
                    how = {"merged": "merged", "saved": "kept next to the new one (.custom)", "unknown": "kept next to the new one (.previous)"}[item["state"]]
                    add("launcher", "info", name=item["name"], how=how)
        ordered = sorted(notices.values(), key=lambda n: (vkey(n["version"]), n["id"]))
        for note in ordered:
            note["rendered"] = notice_text(note, lang)
        blocked = any(c["severity"] == "block" for c in checks)
        return {"installed": installed, "target": to, "direction": direction, "release": {"tag": release["tag"], "name": release["name"], "published": release["published"]},
                "source": getattr(self.source, "kind", "?"), "verified": prep["verified"], "sha256": prep["actual"], "chain": [d["version"] for d in docs], "checks": checks, "blocked": blocked,
                "config": config_plan, "notices": ordered, "launchers": launchers, "steps": list(STEPS), "policy": policy, "mb_needed": need, "mode": inst["mode"], "root": str(self.root),
                "editions": inst["editions"]}

    # --- apply
    def apply(self, target=None, options=None, confirm=None):
        opts = dict(options or {})
        report = {"ok": False, "code": OK, "installed": None, "target": None, "backup": None, "steps": [], "dry_run": bool(opts.get("dry_run")), "rolled_back": False, "error": None, "plan": None}
        try:
            plan = self.plan(target, opts)
        except UpdaterError as error:
            report.update(code=error.code, error=str(error))
            return report
        report.update(installed=plan["installed"], target=plan["target"], plan=plan)
        if plan["blocked"]:
            report.update(code=BLOCKED, error=tr("r.blocked", n=sum(1 for c in plan["checks"] if c["severity"] == "block")))
            return report
        if plan["direction"] == "same" and not opts.get("reinstall"):
            report.update(ok=True, code=OK)
            return report
        if opts.get("dry_run"):
            report.update(ok=True, code=OK)
            return report
        if confirm is not None and not confirm(plan):
            report.update(code=NOT_CONFIRMED, error="not confirmed")
            return report
        if opts.get("handover") and not self.handover_wait(opts):
            report.update(code=BLOCKED, error=tr("c.running", port=next((s["port"] for s in self.detect()["running"].values() if s.get("open") and s.get("ours")), 0)))
            return report
        return self._execute(plan, opts, report)

    def handover_wait(self, opts):
        """Waits (up to handover_timeout seconds, 90 by default) until no monitor of this installation answers: the monitor that asked for the update stops itself right after it started this process."""
        deadline = time.time() + float(opts.get("handover_timeout", 90))
        while True:
            if not any(s.get("open") and s.get("ours") for s in self.detect()["running"].values()):
                return True
            if time.time() >= deadline:
                return False
            time.sleep(0.5)

    def _step(self, report, journal, name, func):
        self.emit(name, "start")
        started = time.time()
        try:
            result = func()
        except BaseException as error:
            report["steps"].append({"step": name, "status": "failed", "detail": str(error)[:200]})
            self.emit(name, "failed", str(error)[:200])
            raise
        report["steps"].append({"step": name, "status": "done", "detail": "", "seconds": round(time.time() - started, 2)})
        journal["steps"][name] = "done"
        self._write_journal(journal)
        self.emit(name, "done")
        return result

    def _write_journal(self, journal):
        path = Path(journal["dir"]) / "journal.json"
        path.write_text(json.dumps({k: v for k, v in journal.items() if k != "dir"}, indent=1), encoding="utf-8")

    def _execute(self, plan, opts, report):
        release = self.resolve_target(plan["target"])
        prep = self.prepare(release)
        if not prep["sha_ok"]:
            report.update(code=FETCH_FAILED, error=tr("c.sha"))
            return report
        folders = self.folders()
        installed, to = plan["installed"], plan["target"]
        stamp = now_stamp()
        bk = self.backups / f"{stamp}_{installed}_to_{to}"
        journal = {"dir": str(bk), "status": "applying", "from": installed, "to": to, "stamp": stamp, "steps": {}, "monitor_started": False, "policy": plan["policy"], "data_schema": data_schema_of(folders)}
        started_process = {"proc": None}
        lock = self.backups / ".lock"
        try:
            self.emit("lock", "start")
            self._take_lock(lock)
            report["steps"].append({"step": "lock", "status": "done", "detail": ""})
            self.emit("lock", "done")
        except UpdaterError as error:
            report.update(code=BLOCKED, error=str(error))
            return report
        report["backup"] = str(bk)
        try:
            private_dir(bk)
            self._write_journal(journal)
            product = self._step(report, journal, "extract", lambda: self.unpack(prep, release))
            registry = load_registry(product, self.root)
            manifest = self._step(report, journal, "backup", lambda: self._snapshot(bk, folders))
            journal["manifest"] = True
            self._step(report, journal, "copy", lambda: self._copy_product(product))
            self._step(report, journal, "retire", lambda: self._retire(product, bk, manifest))
            launchers = self._step(report, journal, "launchers", lambda: self._launchers(product, registry, bk, installed))
            report["launchers"] = [{"name": n, "state": s} for n, s in launchers]
            report["config"] = self._step(report, journal, "config", lambda: self._migrate_configs(registry, installed, to, plan["policy"], folders))
            self._step(report, journal, "layout", lambda: self._layout(installed))
            self._step(report, journal, "verify", lambda: self._verify(to))
            if opts.get("start"):
                self._step(report, journal, "start", lambda: self._start(plan, to, journal, started_process, opts))
            journal["status"] = "done"
            self._write_journal(journal)
            self._history({"result": "ok", "from": installed, "to": to, "backup": bk.name, "source": plan["source"], "notices": [n["id"] for n in plan["notices"]], "steps": len(report["steps"])}, folders)
            report.update(ok=True, code=OK)
        except BaseException as error:        # noqa: B902 - everything that stops the update is answered with a return to the previous state
            if isinstance(error, KeyboardInterrupt):
                pass
            report["error"] = str(error)[:300]
            self.emit("rollback", "start")
            journal["status"] = "rolling_back"
            with contextlib.suppress(OSError):
                self._write_journal(journal)
            try:
                if started_process["proc"] is not None:
                    with contextlib.suppress(OSError):
                        started_process["proc"].terminate()
                        started_process["proc"].wait(timeout=10)
                self.restore(bk, restore_data=bool(journal.get("monitor_started")) or "start" in journal["steps"])
                if opts.get("handover"):
                    with contextlib.suppress(BaseException):      # the monitor that was stopped for the update comes back in the version it had
                        self._start(plan, installed, journal, {"proc": None}, dict(opts, start_timeout=60))
                journal["status"] = "rolled_back"
                self._write_journal(journal)
                report.update(rolled_back=True, code=ROLLED_BACK)
                self._history({"result": "rolled_back", "from": installed, "to": to, "backup": bk.name, "source": plan["source"], "error": report["error"]}, folders)
                self.emit("rollback", "done")
            except BaseException as error2:     # noqa: B902
                journal["status"] = "rollback_failed"
                with contextlib.suppress(OSError):
                    self._write_journal(journal)
                report.update(code=ROLLBACK_FAILED, error2=str(error2)[:300])
                self.emit("rollback", "failed", str(error2)[:200])
        finally:
            with contextlib.suppress(OSError):
                lock.unlink()
            self.cleanup()
            with contextlib.suppress(OSError):
                (bk / "report.json").write_text(json.dumps({k: v for k, v in report.items() if k != "plan"}, indent=1, default=str), encoding="utf-8")
                (bk / "report.txt").write_text(render_result(report), encoding="utf-8")
        return report

    def _take_lock(self, lock):
        private_dir(self.backups)
        if self.lock_state():
            raise UpdaterError(BLOCKED, tr("c.locked"))
        if lock.exists():
            lock.unlink()
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "time": time.time()}, handle)

    def _snapshot(self, bk, folders):
        manifest = {"format": 1, "files": {}, "folders": {k: str(v) for k, v in folders.items()}, "root": str(self.root)}
        for area, rel, path in inventory(self.root, folders):
            if not path.is_file():
                continue
            key = f"{area}/{rel}"
            copy_file(path, bk / "files" / area / rel)
            manifest["files"][key] = {"area": area, "rel": rel, "size": path.stat().st_size}
        (bk / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        return manifest

    def _copy_product(self, product):
        count = 0
        for dirpath, dirnames, filenames in os.walk(product):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for filename in filenames:
                path = Path(dirpath) / filename
                rel = path.relative_to(product).as_posix()
                if classify_member(rel) != "product":
                    continue
                copy_file(path, self.root / rel)
                count += 1
        return count

    def _retire(self, product, bk, manifest):
        moved = []
        prefix = "product/src/github_actions_monitor/"
        for key, meta in manifest["files"].items():
            if key.startswith(prefix) and not (Path(product) / meta["rel"]).exists():
                current = self.root / meta["rel"]
                if current.is_file():
                    move_aside(current, bk / "retired", meta["rel"])
                    moved.append(meta["rel"])
        return moved

    def _launchers(self, product, registry, bk, installed):
        def read_old(name):
            p = bk / "files" / "product" / name
            return p.read_bytes() if p.is_file() else None
        result = []
        for item in resolve_launchers(read_old, product, registry, installed):
            target = self.root / item["name"]
            if item["state"] in ("merged",):
                temp = target.with_name(f".{target.name}.upd{secrets.token_hex(3)}")
                temp.write_bytes(item["data"])
                shutil.copystat(str(Path(product) / item["name"]), str(temp))
                os.replace(str(temp), str(target))
            elif item["state"] in ("saved", "unknown"):
                suffix = ".custom" if item["state"] == "saved" else ".previous"
                (self.root / (item["name"] + suffix)).write_bytes(item["custom"])
            result.append((item["name"], item["state"]))
        return result

    def _migrate_configs(self, registry, installed, to, policy, folders):
        done = []
        docs = registry.chain(installed, to) if vkey(to) > vkey(installed) else []
        if not docs:
            return done
        for path in config_files(self.root, folders):
            data, _dups, error = load_json_strict(path)
            if error or not isinstance(data, dict):
                continue
            migrated, changes, _notes = migrate_config(data, docs, policy)
            if migrated != data:
                dump_config(path, migrated)
            done.append({"file": str(path), "changes": changes})
        return done

    def _layout(self, installed):
        flat = vkey(installed) < vkey("1.8.2") or any(p.suffix == ".py" for p in self.root.glob("*.py"))
        script = self.root / "tools" / "migrate_layout.py"
        if flat and script.is_file():
            done = run_quiet([sys.executable, "-I", str(script), str(self.root), "--apply"], timeout=180)
            if done.returncode != 0:
                raise RuntimeError("migrate_layout failed: " + (done.stderr or done.stdout)[-200:])
        return flat

    def _verify(self, to):
        found = read_tool_version(self.root)
        if found != to:
            raise RuntimeError(f"installed version is {found}, expected {to}")

    def _start(self, plan, to, journal, holder, opts):
        edition = opts.get("edition") or (plan["editions"][0] if plan["editions"] else "complete")
        ports = ports_of(self.detect_config())
        port = ports["lite" if edition == "lite" else "complete"]
        module = "github_actions_monitor.lite" if edition == "lite" else "github_actions_monitor"
        env = dict(self.env)
        env["PYTHONPATH"] = str(self.root / "src") + os.pathsep + env.get("PYTHONPATH", "")
        logs = self.folders()["logs"]
        logs.mkdir(parents=True, exist_ok=True)
        log = open(logs / "updater_start.log", "ab")
        # CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW: a hidden console that the git and gh calls of the monitor inherit (a process without a console would give each of them a window of its own)
        kwargs = {"creationflags": 0x00000200 | 0x08000000} if os.name == "nt" else {"start_new_session": True}
        holder["proc"] = subprocess.Popen([sys.executable, "-m", module, "--no-browser", "--port", str(port)], cwd=str(self.root), env=env, stdout=log, stderr=log, stdin=subprocess.DEVNULL, **kwargs)
        journal["monitor_started"] = True
        deadline = time.time() + float(opts.get("start_timeout", 90))
        while time.time() < deadline:
            if holder["proc"].poll() is not None:
                raise RuntimeError("the monitor stopped right after starting (see logs/updater_start.log)")
            state = self.probe(port)
            if state.get("ours"):
                if state.get("version") and vkey(state["version"]) != vkey(to):
                    raise RuntimeError(f"the monitor answers version {state['version']}, expected {to}")
                holder["proc"] = None            # it is healthy: leave it running
                return state
            time.sleep(1.0)
        raise RuntimeError(f"the monitor did not answer /api/health on port {port}")

    def detect_config(self):
        for path in config_files(self.root, self.folders()):
            if path.name == "actions_monitor.json" and "accounts" not in path.parts:
                return load_json_strict(path)[0]
        return None

    # --- restore (automatic rollback and 'go back')
    def restore(self, bk, restore_data=False):
        bk = Path(bk)
        manifest = json.loads((bk / "manifest.json").read_text(encoding="utf-8"))
        folders = {k: Path(v) for k, v in manifest["folders"].items()}
        areas = {"product", "config", "rootuser"} | ({"data", "ai"} if restore_data else set())
        wanted = {key: meta for key, meta in manifest["files"].items() if meta["area"] in areas}
        current = {f"{a}/{r}": p for a, r, p in inventory(self.root, folders) if a in areas}
        for key, path in current.items():
            if key not in wanted and not key.startswith("rootuser/"):
                move_aside(path, bk / "rolled_back", key)
        for key, meta in wanted.items():
            copy_file(bk / "files" / meta["area"] / meta["rel"], base_of(meta["area"], self.root, folders) / meta["rel"])
        return {"restored": len(wanted), "data": restore_data}

    def history(self):
        path = self.folders()["data"] / HISTORY_NAME
        out = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                with contextlib.suppress(ValueError):
                    out.append(json.loads(line))
        except OSError:
            pass
        return out

    def _history(self, entry, folders):
        folders["data"].mkdir(parents=True, exist_ok=True)
        entry = dict(entry, at=iso_now(), updater=UPDATER_VERSION)
        with open(folders["data"] / HISTORY_NAME, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def previous(self):
        """The last successful update whose copy still exists and that has not been undone, or None."""
        undone = {e.get("undid") for e in self.history() if e.get("result") == "manual_rollback"}
        for entry in reversed(self.history()):
            if entry.get("result") == "ok" and entry.get("backup") not in undone and (self.backups / entry.get("backup", "-") / "manifest.json").is_file():
                return entry
        return None

    def go_back(self, restore_data=None, confirm=None, handover=False):
        report = {"ok": False, "code": OK, "error": None}
        entry = self.previous()
        if not entry:
            report.update(code=USAGE, error=tr("r.no_previous"))
            return report
        if handover:
            self.handover_wait({})
        inst = self.detect()
        for edition, state in inst["running"].items():
            if state.get("open") and state.get("ours"):
                report.update(code=BLOCKED, error=tr("c.running", port=state["port"]))
                return report
        if confirm is not None and not confirm(entry):
            report.update(code=NOT_CONFIRMED, error="not confirmed")
            return report
        bk = self.backups / entry["backup"]
        folders = self.folders()
        if restore_data is None:
            registry = load_registry(None, self.root)
            want = (registry.docs.get(entry["from"]) or {}).get("data_schema")
            restore_data = bool(want and data_schema_of(folders) > want)
        self.restore(bk, restore_data=restore_data)
        self._history({"result": "manual_rollback", "from": entry["to"], "to": entry["from"], "undid": entry["backup"], "backup": entry["backup"]}, folders)
        report.update(ok=True, to=entry["from"], backup=str(bk), data=restore_data)
        if handover:
            with contextlib.suppress(BaseException):      # the monitor that was stopped for the return comes back in the version that was restored
                self._start({"editions": self.detect(probing=False)["editions"]}, entry["from"], {"steps": {}}, {"proc": None}, {"start_timeout": 60})
        return report

    # --- the configuration alone (containers, volumes)
    def migrate_only(self, frm, to, config_paths, policy="conservative", apply=False, registry=None):
        registry = registry or load_registry(None, self.root)
        docs = registry.chain(frm, to) if vkey(to) > vkey(frm) else []
        report = {"from": frm, "to": to, "files": [], "applied": bool(apply), "notices": {}, "gaps": []}
        schema_to = registry.schema_at(to)
        stamp = now_stamp()
        for path in config_paths:
            path = Path(path)
            data, duplicates, error = load_json_strict(path)
            entry = {"file": str(path), "changes": [], "issues": [], "error": error}
            if not error and isinstance(data, dict):
                migrated, changes, notes = migrate_config(data, docs, policy)
                entry["changes"] = changes
                entry["issues"] = [{"code": c, "severity": s, "params": p, "text": tr("c." + c, **p)} for c, s, p in check_config(migrated, schema_to, to)]
                for n in notes:
                    report["notices"][n["id"]] = dict(n, rendered=notice_text(n))
                if apply and migrated != data:
                    private_dir(self.backups / f"migrate_{stamp}")
                    copy_file(path, self.backups / f"migrate_{stamp}" / path.name)
                    dump_config(path, migrated)
            report["files"].append(entry)
        return report


# ---------------------------------------------------------------------------------------------------------------------------------------------
# Text for people
# ---------------------------------------------------------------------------------------------------------------------------------------------
def _short(value):
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= 48 else text[:45] + "..."


def _change_text(change):
    kind = change["type"]
    if kind == "renamed":
        return tr("ch.renamed", old=change["key"], new=change["new_key"])
    if kind == "removed":
        return tr("ch.removed", key=change["key"])
    return tr("ch." + kind, key=change["key"], old=_short(change.get("old")), new=_short(change.get("new")))


def render_state(inst):
    lines = [f"{tr('lbl.folder')}: {inst['root']}", f"{tr('lbl.installed')}: {inst['version'] or tr('lbl.unknown')}  ({inst['layout']})",
             f"{tr('lbl.edition')}: {', '.join(inst['editions'])}", f"{tr('lbl.mode')}: {tr('mode.' + inst['mode'])}",
             f"{tr('lbl.config')}: {', '.join(inst['configs']) or tr('lbl.none')}", f"{tr('lbl.data')}: {inst['folders']['data']}"]
    for edition, state in inst["running"].items():
        lines.append(f"{tr('lbl.running')} ({edition}, :{state['port']}): " + (tr("lbl.yes") + (f" {state['version']}" if state.get("version") else "") if state.get("open") else tr("lbl.no")))
    return "\n".join(lines)


def render_releases(rels):
    lines = [tr("sec.releases")]
    for r in rels:
        marks = []
        if r.get("latest"):
            marks.append(tr("lbl.latest"))
        if r["relation"] == "current":
            marks.append(tr("lbl.current"))
        elif r["relation"] == "newer":
            marks.append(tr("lbl.newer"))
        else:
            marks.append(tr("lbl.older"))
        lines.append(f"  {r['version']:<10} {(r.get('published') or '')[:10]:<11} {', '.join(marks):<24} {r.get('name', '')[:70]}")
    return "\n".join(lines)


def render_plan(plan):
    lines = [f"{plan['installed']} -> {plan['target']}  [{tr('dir.' + plan['direction'])}]  ({plan['source']}, SHA-256 {'OK' if plan['verified'] else tr('lbl.unknown')})"]
    if plan["chain"]:
        lines.append("  " + ", ".join(plan["chain"]))
    lines.append("")
    lines.append(tr("sec.checks"))
    if not plan["checks"]:
        lines.append("  OK")
    for c in plan["checks"]:
        lines.append(f"  [{tr('sev.' + c['severity'])}] {c['text']}")
    lines.append("")
    lines.append(tr("sec.config"))
    any_change = False
    for entry in plan["config"]:
        for change in entry["changes"]:
            any_change = True
            lines.append(f"  {Path(entry['file']).name}: {_change_text(change)}")
    if not any_change:
        lines.append("  " + tr("ch.none"))
    if plan["notices"]:
        lines.append("")
        lines.append(tr("sec.notices"))
        for n in plan["notices"]:
            lines.append(f"  [{n['version']}] {n['rendered']}")
    lines.append("")
    lines.append(tr("sec.steps") + ": " + " > ".join(tr("st." + s) for s in plan["steps"] if s != "start" or plan.get("start")))
    return "\n".join(lines)


def render_result(report, steps=True):
    lines = []
    if report.get("dry_run") and report.get("ok"):
        lines.append(tr("r.dry"))
    elif report.get("ok"):
        lines.append(tr("r.ok", to=report.get("target"), backup=report.get("backup")))
    elif report.get("rolled_back"):
        lines.append(tr("r.rolled", error=report.get("error"), backup=report.get("backup")))
    elif report.get("code") == ROLLBACK_FAILED:
        lines.append(tr("r.rollback_failed", error=report.get("error"), error2=report.get("error2"), backup=report.get("backup")))
    elif report.get("error"):
        lines.append(str(report["error"]))
    for step in (report.get("steps", []) if steps else []):
        lines.append(f"  {tr('st.' + step['step'])}: {tr('st.' + step['status']) if step['status'] in ('done', 'failed', 'skipped') else step['status']}" + (f" ({step['detail']})" if step.get("detail") else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------------------------------------------------------
# Interface 1: the page in the browser (127.0.0.1, a token that exists only while this runs, no dependencies)
# ---------------------------------------------------------------------------------------------------------------------------------------------
PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Monitor updater</title>
<style nonce="@@NONCE@@">
:root{--bg:#0a0b10;--panel:#14161f;--panel2:#202430;--line:#2e3444;--text:#f1f5f9;--mut:#94a3b8;--ok:#22c55e;--bad:#ef4444;--run:#60a5fa;--warn:#f59e0b;--ink:#0b0e14}
@media (prefers-color-scheme:light){:root{--bg:#e4e7ec;--panel:#f4f6f9;--panel2:#e9ecf1;--line:#c7ccd6;--text:#16202c;--mut:#4b5563;--ok:#15803d;--bad:#b91c1c;--run:#1d4ed8;--warn:#b45309;--ink:#fff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,Segoe UI,sans-serif}
header{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:12px 16px;background:var(--panel);border-bottom:1px solid var(--line);flex-wrap:wrap}
h1{font-size:18px;margin:0}h2{font-size:14px;margin:0 0 8px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
main{max-width:980px;margin:0 auto;padding:16px;display:grid;gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;margin:0}dt{color:var(--mut)}dd{margin:0;word-break:break-all}
table{width:100%;border-collapse:collapse}td,th{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}tr.sel{background:var(--panel2)}tr.rel{cursor:pointer}
button,select{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:8px 12px;font:inherit}button{cursor:pointer}button.primary{background:var(--run);color:var(--ink);border-color:var(--run);font-weight:600}button.danger{border-color:var(--bad)}button:disabled{opacity:.5;cursor:default}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.tag{font-size:12px;border:1px solid var(--line);border-radius:99px;padding:1px 8px;color:var(--mut)}
.sev{font-weight:700;margin-right:6px}.sev.block{color:var(--bad)}.sev.warn{color:var(--warn)}.sev.info{color:var(--run)}.ok{color:var(--ok)}.bad{color:var(--bad)}
ul{margin:4px 0;padding-left:20px}pre{white-space:pre-wrap;margin:0}.muted{color:var(--mut)}label{display:block;margin:4px 0}
</style></head><body>
<header><h1 id="title">Monitor updater</h1><div class="row"><select id="lang" aria-label="language"></select><button id="quit"></button></div></header>
<main>
<section class="card"><h2 id="h_inst"></h2><dl id="inst"></dl><div class="row" style="margin-top:10px"><button id="refresh"></button><button id="history"></button></div></section>
<section class="card"><h2 id="h_rel"></h2><div id="relmsg" class="muted"></div><table><tbody id="rels"></tbody></table>
<div class="row" style="margin-top:10px"><button id="zipbtn"></button><input id="zippath" size="40" placeholder="/path/github_actions_monitor.zip"><input id="zipsha" size="22" placeholder="SHA-256"></div></section>
<section class="card"><h2 id="h_opt"></h2><label><input type="radio" name="pol" value="conservative" checked> <span id="o_cons"></span></label>
<label><input type="radio" name="pol" value="keep_old"> <span id="o_keep"></span></label><label><input type="radio" name="pol" value="adopt_new"> <span id="o_adopt"></span></label>
<label><input type="checkbox" id="start"> <span id="o_start"></span></label><div class="muted" id="polnote"></div>
<div class="row" style="margin-top:10px"><button id="plan" class="primary"></button><button id="apply" class="danger" disabled></button><button id="rollback" class="danger"></button></div></section>
<section class="card" id="plancard" hidden><h2 id="h_plan"></h2><div id="planbox"></div></section>
<section class="card" id="progcard" hidden><h2 id="h_prog"></h2><ul id="prog"></ul><pre id="result"></pre></section>
<section class="card" id="histcard" hidden><h2 id="h_hist"></h2><pre id="histbox"></pre></section>
</main>
<script nonce="@@NONCE@@">
"use strict";
const TOKEN="@@TOKEN@@";let T={},selected=null,planned=null,polling=null;
history.replaceState(null,"",location.pathname);
const $=id=>document.getElementById(id);
async function api(path,body){const o={headers:{"X-Updater-Token":TOKEN}};if(body!==undefined){o.method="POST";o.headers["Content-Type"]="application/json";o.body=JSON.stringify(body)}const r=await fetch(path,o);return r.json()}
function el(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e}
function tt(k,v){let s=T[k]||k;if(v)for(const a in v)s=s.split("{"+a+"}").join(v[a]);return s}
function setTexts(){document.documentElement.lang=$("lang").value;document.title=T["app.title"];$("title").textContent=T["app.title"];
 const m={h_inst:"lbl.installed",h_rel:"sec.releases",h_opt:"lbl.target",h_plan:"sec.plan",h_prog:"sec.progress",h_hist:"btn.history",refresh:"btn.refresh",history:"btn.history",zipbtn:"btn.zip",plan:"btn.plan",apply:"btn.apply",rollback:"btn.rollback",quit:"btn.quit",o_cons:"opt.policy_note",o_keep:"opt.keep_old",o_adopt:"opt.adopt_new",o_start:"opt.start"};
 for(const id in m)$(id).textContent=T[m[id]];$("h_opt").textContent=T["sec.steps"]}
async function loadCatalog(){const c=await api("/api/catalog?lang="+$("lang").value);T=c.catalog;setTexts()}
function row(dl,k,v){dl.appendChild(el("dt",k));dl.appendChild(el("dd",v))}
async function loadState(){const s=await api("/api/state");const dl=$("inst");dl.textContent="";
 row(dl,T["lbl.folder"],s.root);row(dl,T["lbl.installed"],(s.version||T["lbl.unknown"])+" ("+s.layout+")");row(dl,T["lbl.edition"],s.editions.join(", "));row(dl,T["lbl.mode"],T["mode."+s.mode]);
 row(dl,T["lbl.config"],s.configs.join(", ")||T["lbl.none"]);row(dl,T["lbl.data"],s.folders.data);
 for(const e in s.running){const r=s.running[e];row(dl,T["lbl.running"]+" ("+e+", :"+r.port+")",r.open?(T["lbl.yes"]+(r.version?" "+r.version:"")):T["lbl.no"])}}
async function loadReleases(){const r=await api("/api/releases");const tb=$("rels");tb.textContent="";$("relmsg").textContent="";
 if(r.error){$("relmsg").textContent=r.error;return}
 for(const x of r.releases){const tr=el("tr");tr.className="rel"+(selected===x.version?" sel":"");const tags=[];if(x.latest)tags.push(T["lbl.latest"]);tags.push(T["lbl."+x.relation]);
  tr.appendChild(el("td",x.version));tr.appendChild(el("td",(x.published||"").slice(0,10)));const tg=el("td");for(const g of tags)tg.appendChild(el("span",g,"tag"));tr.appendChild(tg);tr.appendChild(el("td",x.name));
  tr.addEventListener("click",()=>{selected=x.version;planned=null;$("apply").disabled=true;loadReleases()});tb.appendChild(tr)}}
function pol(){return document.querySelector("input[name=pol]:checked").value}
function renderPlan(p){const b=$("planbox");b.textContent="";$("plancard").hidden=false;
 b.appendChild(el("div",p.installed+" → "+p.target+"  ["+T["dir."+p.direction]+"]  "+(p.verified?"SHA-256 OK":"")));
 b.appendChild(el("h2",T["sec.checks"]));const u=el("ul");if(!p.checks.length)u.appendChild(el("li","OK","ok"));
 for(const c of p.checks){const li=el("li");li.appendChild(el("span",T["sev."+c.severity],"sev "+c.severity));li.appendChild(document.createTextNode(c.text));u.appendChild(li)}b.appendChild(u);
 b.appendChild(el("h2",T["sec.config"]));const u2=el("ul");let n=0;for(const f of p.config)for(const ch of f.changes){n++;u2.appendChild(el("li",ch.text||""))}if(!n)u2.appendChild(el("li",T["ch.none"]));b.appendChild(u2);
 if(p.notices.length){b.appendChild(el("h2",T["sec.notices"]));const u3=el("ul");for(const x of p.notices)u3.appendChild(el("li","["+x.version+"] "+x.rendered));b.appendChild(u3)}
 $("apply").disabled=p.blocked||p.direction==="same"}
async function doPlan(){if(!selected){$("relmsg").textContent=T["web.choose_version"];return}$("plan").disabled=true;
 const p=await api("/api/plan",{target:selected,policy:pol(),start:$("start").checked});$("plan").disabled=false;
 if(p.error){$("plancard").hidden=false;$("planbox").textContent=p.error;return}planned=p;renderPlan(p)}
async function poll(){const j=await api("/api/progress");const u=$("prog");u.textContent="";$("progcard").hidden=false;
 for(const e of j.events)u.appendChild(el("li",(T["st."+e.step]||e.step)+": "+(T["st."+e.status]||e.status)+(e.detail?" ("+e.detail+")":"")));
 if(j.running){polling=setTimeout(poll,800)}else{$("result").textContent=j.text||"";$("apply").disabled=true;loadState();loadReleases()}}
async function doApply(){if(!planned||!confirm(T["web.confirm_apply"]))return;$("apply").disabled=true;
 const r=await api("/api/apply",{target:planned.target,policy:pol(),start:$("start").checked,allow_downgrade:planned.direction==="downgrade"});
 if(r.error){$("progcard").hidden=false;$("result").textContent=r.error;return}poll()}
async function doRollback(){if(!confirm(T["btn.rollback"]+"?"))return;const r=await api("/api/rollback",{});$("progcard").hidden=false;$("result").textContent=r.text||r.error||"";loadState()}
async function doHistory(){const h=await api("/api/history");$("histcard").hidden=false;$("histbox").textContent=h.text||""}
async function doZip(){const r=await api("/api/zip",{path:$("zippath").value,sha256:$("zipsha").value});if(r.error){$("relmsg").textContent=r.error;return}selected=null;loadReleases()}
async function init(){const langs=["en","es","de","fr","it","ja","zh","pt"];const names={en:"English",es:"Español",de:"Deutsch",fr:"Français",it:"Italiano",ja:"日本語",zh:"中文",pt:"Português"};
 for(const l of langs){const o=el("option",names[l]);o.value=l;$("lang").appendChild(o)}const first=await api("/api/catalog");$("lang").value=first.lang;T=first.catalog;setTexts();
 $("lang").addEventListener("change",async()=>{await loadCatalog();await loadState();await loadReleases();if(planned)renderPlan(planned)});
 $("refresh").addEventListener("click",()=>{loadState();loadReleases()});$("plan").addEventListener("click",doPlan);$("apply").addEventListener("click",doApply);$("rollback").addEventListener("click",doRollback);
 $("history").addEventListener("click",doHistory);$("zipbtn").addEventListener("click",doZip);$("quit").addEventListener("click",async()=>{await api("/api/quit",{});document.body.textContent="OK"});
 await loadState();await loadReleases()}
init();
</script></body></html>"""


class WebApp:
    """The state behind the page: one updater, one job at a time, the token and the port."""

    def __init__(self, make_updater, token=None, lang="en"):
        self.make_updater = make_updater
        self.updater = make_updater(None)
        self.token = token or secrets.token_urlsafe(24)
        self.lang = lang
        self.port = 0
        self.job = {"running": False, "events": [], "text": "", "report": None}
        self.lock = threading.Lock()
        self.stop = threading.Event()

    def catalog(self, lang):
        merged = dict(_CAT["en"])
        merged.update(_CAT.get(lang, {}))
        return merged

    def json_plan(self, plan):
        for entry in plan["config"]:
            for change in entry["changes"]:
                change["text"] = _change_text(change)
        return plan

    def handle(self, method, path, query, body):
        """(status, payload dict). The caller has already checked the token, the host and the origin."""
        up = self.updater
        try:
            if method == "GET" and path == "/api/catalog":
                lang = pick_language((query.get("lang") or [self.lang])[0])
                set_language(lang)
                return 200, {"lang": lang, "catalog": self.catalog(lang)}
            if method == "GET" and path == "/api/state":
                return 200, up.detect()
            if method == "GET" and path == "/api/releases":
                try:
                    return 200, {"releases": up.annotate(refresh_list(up))}
                except UpdaterError as error:
                    return 200, {"error": tr(error.key) if error.key else str(error)}
            if method == "GET" and path == "/api/progress":
                return 200, dict(self.job)
            if method == "GET" and path == "/api/history":
                return 200, {"text": "\n".join(f"{e.get('at', '')}  {e.get('result')}  {e.get('from')} -> {e.get('to')}  {e.get('backup', '')}" for e in up.history()) or tr("lbl.none")}
            if method == "POST" and path == "/api/plan":
                options = {"policy": _policy(body.get("policy")), "start": bool(body.get("start")), "allow_downgrade": True}
                return 200, self.json_plan(up.plan(body.get("target"), options))
            if method == "POST" and path == "/api/apply":
                with self.lock:
                    if self.job["running"]:
                        return 409, {"error": "busy"}
                    self.job = {"running": True, "events": [], "text": "", "report": None}
                options = {"policy": _policy(body.get("policy")), "start": bool(body.get("start")), "allow_downgrade": bool(body.get("allow_downgrade"))}
                threading.Thread(target=self._run_apply, args=(body.get("target"), options), daemon=True).start()
                return 200, {"started": True}
            if method == "POST" and path == "/api/rollback":
                report = up.go_back(restore_data=None)
                text = tr("r.back_ok", to=report.get("to"), backup=report.get("backup")) if report.get("ok") else (report.get("error") or "")
                return 200, {"text": text, "error": None if report.get("ok") else text}
            if method == "POST" and path == "/api/zip":
                zip_path = Path(str(body.get("path") or "")).expanduser()
                if zip_path.suffix.lower() != ".zip" or not zip_path.is_file():
                    return 200, {"error": tr("p.zip") + str(zip_path)}
                self.updater = up = self.make_updater(LocalZipSource(zip_path, body.get("sha256")))
                return 200, {"ok": True}
            if method == "POST" and path == "/api/quit":
                self.stop.set()
                return 200, {"ok": True}
        except UpdaterError as error:
            return 200, {"error": tr(error.key) if error.key and error.key.startswith("r.") else str(error)}
        except Exception as error:      # noqa: BLE001 - a failure of one request must not close the page
            return 500, {"error": str(error)[:200]}
        return 404, {"error": "not found"}

    def _run_apply(self, target, options):
        def emit(event):
            self.job["events"].append(event)
        self.updater.emit_cb = emit
        try:
            report = self.updater.apply(target, options)
            self.job["text"] = render_result(report)
            self.job["report"] = {k: v for k, v in report.items() if k != "plan"}
        except Exception as error:      # noqa: BLE001
            self.job["text"] = str(error)
        finally:
            self.updater.emit_cb = None
            self.job["running"] = False


def refresh_list(updater):
    return updater.releases(refresh=True)


def _policy(value):
    return value if value in ("conservative", "keep_old", "adopt_new") else "conservative"


def make_handler(app):
    from http.server import BaseHTTPRequestHandler
    from urllib.parse import parse_qs, urlparse

    class Handler(BaseHTTPRequestHandler):
        server_version = "MonitorUpdater"
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def _host_ok(self):
            host = (self.headers.get("Host") or "").lower()
            return host in (f"127.0.0.1:{app.port}", f"localhost:{app.port}")

        def _send(self, status, body, ctype, extra=None):
            raw = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(raw)

        def _json(self, status, payload):
            self._send(status, json.dumps(payload, default=str), "application/json; charset=utf-8")

        def _token_ok(self, supplied):
            return bool(supplied) and hmac.compare_digest(str(supplied), app.token)

        def do_GET(self):
            url = urlparse(self.path)
            query = parse_qs(url.query)
            if not self._host_ok():
                return self._json(403, {"error": "host"})
            if url.path == "/":
                if not self._token_ok((query.get("t") or [""])[0]):
                    return self._json(403, {"error": "token"})
                nonce = secrets.token_urlsafe(12)
                page = PAGE.replace("@@NONCE@@", nonce).replace("@@TOKEN@@", app.token)
                csp = f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
                return self._send(200, page, "text/html; charset=utf-8", {"Content-Security-Policy": csp})
            if not url.path.startswith("/api/") or not self._token_ok(self.headers.get("X-Updater-Token")):
                return self._json(403, {"error": "token"})
            status, payload = app.handle("GET", url.path, query, {})
            self._json(status, payload)

        def do_POST(self):
            url = urlparse(self.path)
            if not self._host_ok():
                return self._json(403, {"error": "host"})
            origin = self.headers.get("Origin")
            if origin and origin not in (f"http://127.0.0.1:{app.port}", f"http://localhost:{app.port}"):
                return self._json(403, {"error": "origin"})
            if self.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none"):
                return self._json(403, {"error": "origin"})
            if not url.path.startswith("/api/") or not self._token_ok(self.headers.get("X-Updater-Token")):
                return self._json(403, {"error": "token"})
            if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
                return self._json(415, {"error": "content-type"})
            try:
                size = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(min(size, 65536)).decode("utf-8") or "{}") if size else {}
                if not isinstance(body, dict):
                    raise ValueError
            except ValueError:
                return self._json(400, {"error": "json"})
            status, payload = app.handle("POST", url.path, parse_qs(url.query), body)
            self._json(status, payload)

    return Handler


def serve_web(make_updater, port=0, open_browser=True, lang="en", out=None, ready=None):
    """Runs the page until Quit or Ctrl+C. Returns the exit code."""
    from http.server import ThreadingHTTPServer
    out = out or sys.stdout
    app = WebApp(make_updater, lang=lang)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    server.daemon_threads = True
    app.port = server.server_address[1]
    url = f"http://127.0.0.1:{app.port}/?t={app.token}"
    print(tr("web.listening", url=url), file=out)
    print(tr("web.stop"), file=out)
    if ready:
        ready(app, server, url)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if open_browser:
        with contextlib.suppress(Exception):
            import webbrowser
            webbrowser.open(url)
    try:
        while not app.stop.is_set():
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    server.shutdown()
    server.server_close()
    app.updater.cleanup()
    return OK


# ---------------------------------------------------------------------------------------------------------------------------------------------
# Interface 2: the text menu (servers, SSH, containers)
# ---------------------------------------------------------------------------------------------------------------------------------------------
def console_menu(updater, inp=input, out=None):
    out = out or sys.stdout
    say = lambda text="": print(text, file=out)       # noqa: E731
    say(tr("app.title") + " " + UPDATER_VERSION)
    running = True
    while running:
        say()
        for key in "1234560":
            say(f"  {key}) {tr('menu.' + key)}")
        try:
            choice = inp(tr("p.choose")).strip()
            if choice == "1":
                say(render_state(updater.detect()))
            elif choice == "2":
                say(render_releases(updater.annotate(refresh_list(updater))))
            elif choice in ("3", "4"):
                target = inp(tr("p.version")).strip() or None
                options = {"policy": "conservative", "allow_downgrade": True}
                plan = updater.plan(target, options)
                say(render_plan(plan))
                if choice == "4":
                    if plan["blocked"]:
                        say(tr("r.blocked", n=sum(1 for c in plan["checks"] if c["severity"] == "block")))
                    elif inp(tr("p.confirm")).strip().lower() in ("yes", "y", "si", "sí", "ja", "oui", "sì", "sim", "是", "はい"):
                        updater.emit_cb = lambda e: say(f"  {tr('st.' + e['step'])}: {e['status']}")
                        report = updater.apply(target, dict(options, allow_downgrade=plan["direction"] == "downgrade"))
                        say(render_result(report))
                    else:
                        say(tr("r.dry"))
            elif choice == "5":
                report = updater.go_back()
                say(tr("r.back_ok", to=report.get("to"), backup=report.get("backup")) if report.get("ok") else report.get("error"))
            elif choice == "6":
                for entry in updater.history():
                    say(f"  {entry.get('at', '')}  {entry.get('result')}  {entry.get('from')} -> {entry.get('to')}")
            elif choice in ("0", "q", "Q"):
                return OK
        except UpdaterError as error:
            say(str(error))
        except EOFError:
            return OK


# ---------------------------------------------------------------------------------------------------------------------------------------------
# Interface 3: a window (Tkinter, if it exists)
# ---------------------------------------------------------------------------------------------------------------------------------------------
def run_tk(updater):
    try:
        import tkinter as tk
        from tkinter import messagebox, ttk
        root = tk.Tk()
    except Exception:       # noqa: BLE001 - no Tkinter, or no display
        print(tr("tk.unavailable"), file=sys.stderr)
        return USAGE
    root.title(tr("app.title"))
    root.geometry("900x640")
    state = tk.StringVar()
    versions = ttk.Combobox(root, state="readonly", width=24)
    box = tk.Text(root, wrap="word", height=26)
    queue = []

    def show(text):
        box.delete("1.0", "end")
        box.insert("end", text)

    def refresh():
        try:
            state.set(render_state(updater.detect()))
            rels = updater.annotate(refresh_list(updater))
            versions["values"] = [r["version"] + ("  *" if r.get("latest") else "") for r in rels]
            if rels and not versions.get():
                versions.current(0)
            show(render_releases(rels))
        except UpdaterError as error:
            show(str(error))

    def chosen():
        return versions.get().split()[0] if versions.get() else None

    def do_plan():
        try:
            show(render_plan(updater.plan(chosen(), {"allow_downgrade": True})))
        except UpdaterError as error:
            show(str(error))

    def do_apply():
        try:
            plan = updater.plan(chosen(), {"allow_downgrade": True})
        except UpdaterError as error:
            return show(str(error))
        if plan["blocked"] or not messagebox.askyesno(tr("app.title"), tr("web.confirm_apply")):
            return show(render_plan(plan))
        updater.emit_cb = lambda e: queue.append(f"{tr('st.' + e['step'])}: {e['status']}")

        def work():
            report = updater.apply(chosen(), {"allow_downgrade": plan["direction"] == "downgrade"})
            queue.append(render_result(report))
        threading.Thread(target=work, daemon=True).start()

    def do_back():
        report = updater.go_back()
        show(tr("r.back_ok", to=report.get("to"), backup=report.get("backup")) if report.get("ok") else report.get("error"))

    def pump():
        while queue:
            box.insert("end", queue.pop(0) + "\n")
            box.see("end")
        root.after(400, pump)

    tk.Label(root, textvariable=state, justify="left", anchor="w").pack(fill="x", padx=8, pady=6)
    bar = tk.Frame(root)
    bar.pack(fill="x", padx=8)
    versions.pack(in_=bar, side="left")
    for label, func in ((tr("btn.refresh"), refresh), (tr("btn.plan"), do_plan), (tr("btn.apply"), do_apply), (tr("btn.rollback"), do_back), (tr("btn.quit"), root.destroy)):
        tk.Button(bar, text=label, command=func).pack(side="left", padx=4)
    box.pack(fill="both", expand=True, padx=8, pady=8)
    refresh()
    pump()
    root.mainloop()
    updater.cleanup()
    return OK


# ---------------------------------------------------------------------------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------------------------------------------------------------------------
COMMANDS = ("status", "releases", "plan", "apply", "migrate", "rollback", "history", "web", "tk", "console")


class StatusFile:
    """The progress of an update that the monitor started: a small JSON file the page of the monitor reads (also after the monitor restarted). One writer, replaced atomically."""

    def __init__(self, path, kind):
        self.path = Path(path) if path else None
        self.doc = {"kind": kind, "running": True, "started": iso_now(), "events": [], "text": "", "report": None, "pid": os.getpid()}
        self.write()

    def event(self, event):
        self.doc["events"].append(event)
        self.write()

    def finish(self, text, report):
        self.doc.update(running=False, finished=iso_now(), text=text, report=report)
        self.write()

    def write(self):
        if self.path is None:
            return
        with contextlib.suppress(OSError):
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.doc, default=str), encoding="utf-8")
            os.replace(tmp, self.path)


def build_parser():
    parser = argparse.ArgumentParser(prog="monitor_updater.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", nargs="?", choices=COMMANDS, help="default: web (the page in the browser)")
    parser.add_argument("--dir", help="the installation")
    parser.add_argument("--to", help="target version (default: the latest)")
    parser.add_argument("--from", dest="frm", help="migrate: the version the configuration comes from (default: the installed one)")
    parser.add_argument("--config", action="append", help="migrate: a configuration file (default: the ones of the installation)")
    parser.add_argument("--zip", help="use this zip instead of GitHub")
    parser.add_argument("--sha256", help="expected SHA-256 of --zip")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true", help="migrate: write the result (without it only shows)")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--keep-old-defaults", action="store_true")
    parser.add_argument("--adopt-new-defaults", action="store_true")
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--handover", action="store_true", help="the monitor that started this process stops by itself: wait for it, apply, start it again (a failed start brings the previous version back)")
    parser.add_argument("--status-file", help="write the progress of apply/rollback to this JSON file (the page of the monitor reads it)")
    parser.add_argument("--edition", choices=("complete", "lite"))
    parser.add_argument("--allow-downgrade", action="store_true")
    parser.add_argument("--allow-container", action="store_true", help="work inside a container anyway (the image is not replaced by this)")
    parser.add_argument("--no-gh", action="store_true", help="do not use the gh tool")
    parser.add_argument("--backups", help="folder of copies")
    parser.add_argument("--restore-data", choices=("yes", "no", "auto"), default="auto", help="rollback: bring the data back too")
    parser.add_argument("--port", type=int, default=0, help="web: port of the page (default: any free one)")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--tk", action="store_true")
    parser.add_argument("--console", action="store_true")
    parser.add_argument("--lang")
    return parser


def options_of(args):
    policy = "keep_old" if args.keep_old_defaults else ("adopt_new" if args.adopt_new_defaults else "conservative")
    return {"policy": policy, "dry_run": args.dry_run, "start": args.start, "handover": args.handover, "edition": args.edition, "allow_downgrade": args.allow_downgrade, "allow_container": args.allow_container}


def default_root(args):
    if args.dir:
        return Path(args.dir).resolve()
    for start in (Path(__file__).resolve().parent, Path.cwd()):
        found = find_root(start)
        if found:
            return found
    return None


def main(argv=None, out=None, inp=input):
    out = out or sys.stdout
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            if not stream.isatty():
                stream.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:
        return USAGE if stop.code else OK
    set_language(args.lang)
    if args.keep_old_defaults and args.adopt_new_defaults:
        print("--keep-old-defaults and --adopt-new-defaults exclude each other", file=sys.stderr)
        return USAGE
    root = default_root(args)
    if root is None:
        print(tr("lbl.folder") + ": ?  (--dir)", file=sys.stderr)
        return USAGE

    def make_source(local=None):
        if local is not None:
            return local
        if args.zip:
            return LocalZipSource(args.zip, args.sha256)
        return GitHubSource(prefer_gh=not args.no_gh)

    def make_updater(local=None):
        return Updater(root, make_source(local), backups=args.backups, lang=args.lang)

    command = args.command or ("tk" if args.tk else "console" if args.console else "web")
    say = lambda text="": print(text, file=out)        # noqa: E731
    try:
        if command == "web":
            return serve_web(make_updater, args.port, not args.no_browser, pick_language(args.lang), out=out)
        if command == "tk":
            return run_tk(make_updater())
        if command == "console":
            return console_menu(make_updater(), inp, out)
        updater = make_updater()
        if command == "status":
            info = updater.detect()
            say(json.dumps(info, indent=1) if args.json else render_state(info))
            return OK
        if command == "releases":
            rels = updater.annotate()
            say(json.dumps(rels, indent=1) if args.json else render_releases(rels))
            return OK
        if command == "history":
            entries = updater.history()
            say(json.dumps(entries, indent=1) if args.json else "\n".join(f"{e.get('at', '')}  {e.get('result')}  {e.get('from')} -> {e.get('to')}  {e.get('backup', '')}" for e in entries) or tr("lbl.none"))
            return OK
        if command == "plan":
            plan = updater.plan(args.to, options_of(args))
            say(json.dumps(plan, indent=1, default=str) if args.json else render_plan(plan))
            return BLOCKED if plan["blocked"] else OK
        if command == "apply":
            def confirm(plan):
                if args.yes or args.json:
                    return True
                say(render_plan(plan))
                return inp(tr("p.confirm")).strip().lower() in ("yes", "y", "si", "sí", "ja", "oui", "sì", "sim", "是", "はい")
            status = StatusFile(args.status_file, "apply") if args.status_file else None
            if status is not None:
                updater.emit_cb = status.event
            elif not args.json:
                updater.emit_cb = lambda e: say(f"  {tr('st.' + e['step'])}: {e['status']}")
            report = updater.apply(args.to, options_of(args), confirm)
            if status is not None:
                status.finish(render_result(report) or str(report.get("error") or ""), {k: v for k, v in report.items() if k != "plan"})
            if args.json:
                say(json.dumps({k: v for k, v in report.items() if k != "plan"}, indent=1, default=str))
            else:
                say(render_result(report, steps=False) or str(report.get("error") or ""))
                if report.get("code") == BLOCKED and report.get("plan"):
                    say(render_plan(report["plan"]))
            return report["code"]
        if command == "migrate":
            info = updater.detect(probing=False)
            frm = args.frm or info["version"] or "1.8.1"
            to = args.to or frm
            registry = load_registry(None, root)
            if not args.to and info["version"]:
                to = info["version"]
            paths = [Path(p) for p in (args.config or info["configs"])]
            result = updater.migrate_only(frm, to, paths, options_of(args)["policy"], apply=args.apply, registry=registry)
            if args.json:
                say(json.dumps(result, indent=1, default=str))
            else:
                say(f"{frm} -> {to}" + ("" if args.apply else "  (" + tr("r.dry") + ")"))
                for entry in result["files"]:
                    say(entry["file"] + (": " + str(entry["error"]) if entry.get("error") else ""))
                    for change in entry["changes"]:
                        say("  " + _change_text(change))
                    if not entry["changes"] and not entry.get("error"):
                        say("  " + tr("ch.none"))
                    for issue in entry["issues"]:
                        say(f"  [{tr('sev.' + issue['severity'])}] {issue['text']}")
                for note in result["notices"].values():
                    say(f"  [{note['version']}] {note['rendered']}")
            return OK
        if command == "rollback":
            restore = {"yes": True, "no": False, "auto": None}[args.restore_data]
            status = StatusFile(args.status_file, "rollback") if args.status_file else None
            report = updater.go_back(restore, None if args.yes else (lambda entry: inp(tr("btn.rollback") + f" ({entry['to']} -> {entry['from']})? " + tr("p.confirm")).strip().lower() in ("yes", "y", "si", "sí", "ja", "oui", "sì", "sim", "是", "はい")), handover=args.handover)
            if status is not None:
                status.finish(tr("r.back_ok", to=report.get("to"), backup=report.get("backup")) if report.get("ok") else str(report.get("error")), report)
            if args.json:
                say(json.dumps(report, indent=1, default=str))
            else:
                say(tr("r.back_ok", to=report.get("to"), backup=report.get("backup")) if report.get("ok") else str(report.get("error")))
            return report["code"]
    except UpdaterError as error:
        print(tr(error.key) if error.key and error.key.startswith("r.") else str(error), file=sys.stderr)
        return error.code
    finally:
        pass
    return USAGE


if __name__ == "__main__":
    sys.exit(main())
