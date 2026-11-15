# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Texts that the expansion modules (client API, plugins, proposals, assistant) show to people, in the eight languages of the product (en, es, de, fr, it, ja, zh, pt = European Portuguese).

They live here, next to the code that raises them, so that this package stands on its own; `t(lang, key, **values)` falls back to English and then to the key, and never raises. Codes (the part
a program reads) are stable and never translated; only the human sentence is."""

LANGS = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")

CATALOGUE = {
    "api.bad_request": {
        "en": "The request is not valid: {detail}.", "es": "La petición no es válida: {detail}.", "de": "Die Anfrage ist ungültig: {detail}.",
        "fr": "La requête n'est pas valide : {detail}.", "it": "La richiesta non è valida: {detail}.", "ja": "リクエストが無効です: {detail}。",
        "zh": "请求无效：{detail}。", "pt": "O pedido não é válido: {detail}."},
    "api.unauthorized": {
        "en": "Sign in or send a valid token.", "es": "Inicie sesión o envíe un token válido.", "de": "Melden Sie sich an oder senden Sie ein gültiges Token.",
        "fr": "Connectez-vous ou envoyez un jeton valide.", "it": "Acceda o invii un token valido.", "ja": "サインインするか、有効なトークンを送信してください。",
        "zh": "请登录或发送有效的令牌。", "pt": "Inicie sessão ou envie um token válido."},
    "api.forbidden": {
        "en": "Your role does not allow this.", "es": "Su rol no permite esto.", "de": "Ihre Rolle erlaubt dies nicht.",
        "fr": "Votre rôle ne le permet pas.", "it": "Il suo ruolo non lo consente.", "ja": "このロールでは許可されていません。",
        "zh": "您的角色不允许此操作。", "pt": "A sua função não permite isto."},
    "api.not_found": {
        "en": "Nothing was found here.", "es": "No se ha encontrado nada aquí.", "de": "Hier wurde nichts gefunden.",
        "fr": "Rien n'a été trouvé ici.", "it": "Non è stato trovato nulla.", "ja": "該当するものが見つかりません。",
        "zh": "未找到任何内容。", "pt": "Não foi encontrado nada aqui."},
    "api.bad_cursor": {
        "en": "The cursor is not valid or has expired.", "es": "El cursor no es válido o ha caducado.", "de": "Der Cursor ist ungültig oder abgelaufen.",
        "fr": "Le curseur n'est pas valide ou a expiré.", "it": "Il cursore non è valido o è scaduto.", "ja": "カーソルが無効か、期限切れです。",
        "zh": "游标无效或已过期。", "pt": "O cursor não é válido ou expirou."},
    "api.bad_limit": {
        "en": "The limit must be a whole number between 1 and {max}.", "es": "El límite debe ser un entero entre 1 y {max}.",
        "de": "Das Limit muss eine ganze Zahl zwischen 1 und {max} sein.", "fr": "La limite doit être un entier entre 1 et {max}.",
        "it": "Il limite deve essere un intero tra 1 e {max}.", "ja": "limit は 1 から {max} までの整数にしてください。",
        "zh": "limit 必须是 1 到 {max} 之间的整数。", "pt": "O limite tem de ser um número inteiro entre 1 e {max}."},
    "api.unknown_field": {
        "en": "Unknown field: {field}.", "es": "Campo desconocido: {field}.", "de": "Unbekanntes Feld: {field}.", "fr": "Champ inconnu : {field}.",
        "it": "Campo sconosciuto: {field}.", "ja": "不明なフィールド: {field}。", "zh": "未知字段：{field}。", "pt": "Campo desconhecido: {field}."},
    "api.version_unsupported": {
        "en": "API version {version} is not supported.", "es": "La versión {version} de la API no está soportada.",
        "de": "API-Version {version} wird nicht unterstützt.", "fr": "La version {version} de l'API n'est pas prise en charge.",
        "it": "La versione {version} dell'API non è supportata.", "ja": "API バージョン {version} はサポートされていません。",
        "zh": "不支持 API 版本 {version}。", "pt": "A versão {version} da API não é suportada."},
    "api.server_error": {
        "en": "The monitor could not answer this request.", "es": "El monitor no ha podido responder a esta petición.",
        "de": "Der Monitor konnte diese Anfrage nicht beantworten.", "fr": "Le moniteur n'a pas pu répondre à cette requête.",
        "it": "Il monitor non ha potuto rispondere a questa richiesta.", "ja": "モニターはこのリクエストに応答できませんでした。",
        "zh": "监视器无法响应此请求。", "pt": "O monitor não conseguiu responder a este pedido."},
    "plugin.invalid_manifest": {
        "en": "Plugin manifest rejected: {reason}.", "es": "Manifiesto de plugin rechazado: {reason}.", "de": "Plugin-Manifest abgelehnt: {reason}.",
        "fr": "Manifeste du plugin refusé : {reason}.", "it": "Manifest del plugin rifiutato: {reason}.", "ja": "プラグインのマニフェストを拒否しました: {reason}。",
        "zh": "插件清单被拒绝：{reason}。", "pt": "Manifesto do plugin rejeitado: {reason}."},
    "plugin.not_loaded_untrusted": {
        "en": "Plugin {name} was not loaded: third-party plugins run with the same power as the monitor and are off.",
        "es": "El plugin {name} no se ha cargado: los plugins de terceros tienen el mismo poder que el monitor y están desactivados.",
        "de": "Plugin {name} wurde nicht geladen: Plugins von Dritten haben dieselbe Macht wie der Monitor und sind ausgeschaltet.",
        "fr": "Le plugin {name} n'a pas été chargé : les plugins tiers ont le même pouvoir que le moniteur et sont désactivés.",
        "it": "Il plugin {name} non è stato caricato: i plugin di terzi hanno lo stesso potere del monitor e sono disattivati.",
        "ja": "プラグイン {name} は読み込まれませんでした。サードパーティ製プラグインはモニターと同じ権限で動作するため、無効になっています。",
        "zh": "未加载插件 {name}：第三方插件与监视器拥有相同权限，默认关闭。",
        "pt": "O plugin {name} não foi carregado: os plugins de terceiros têm o mesmo poder que o monitor e estão desativados."},
    "plugin.failed": {
        "en": "Plugin {name} failed and was set aside; the rest of the monitor keeps running.",
        "es": "El plugin {name} ha fallado y se ha apartado; el resto del monitor sigue funcionando.",
        "de": "Plugin {name} ist fehlgeschlagen und wurde beiseitegelegt; der Rest des Monitors läuft weiter.",
        "fr": "Le plugin {name} a échoué et a été mis de côté ; le reste du moniteur continue de fonctionner.",
        "it": "Il plugin {name} ha fallito ed è stato messo da parte; il resto del monitor continua a funzionare.",
        "ja": "プラグイン {name} が失敗したため、除外しました。モニターの他の部分は動作し続けます。",
        "zh": "插件 {name} 出错并已被搁置；监视器的其余部分继续运行。",
        "pt": "O plugin {name} falhou e foi posto de parte; o resto do monitor continua a funcionar."},
    "act.not_allowed": {
        "en": "The policy does not allow this action: {reason}.", "es": "La política no permite esta acción: {reason}.",
        "de": "Die Richtlinie erlaubt diese Aktion nicht: {reason}.", "fr": "La politique n'autorise pas cette action : {reason}.",
        "it": "La policy non consente questa azione: {reason}.", "ja": "ポリシーによりこの操作は許可されていません: {reason}。",
        "zh": "策略不允许此操作：{reason}。", "pt": "A política não permite esta ação: {reason}."},
    "act.hash_mismatch": {
        "en": "The proposal changed after it was approved; approve it again.", "es": "La propuesta cambió después de aprobarse; apruébela de nuevo.",
        "de": "Der Vorschlag wurde nach der Genehmigung geändert; genehmigen Sie ihn erneut.",
        "fr": "La proposition a changé après son approbation ; approuvez-la à nouveau.",
        "it": "La proposta è cambiata dopo l'approvazione; la approvi di nuovo.", "ja": "承認後に提案が変更されました。もう一度承認してください。",
        "zh": "提案在批准后已更改，请重新批准。", "pt": "A proposta mudou depois de aprovada; aprove-a de novo."},
    "act.expired": {
        "en": "The proposal has expired.", "es": "La propuesta ha caducado.", "de": "Der Vorschlag ist abgelaufen.", "fr": "La proposition a expiré.",
        "it": "La proposta è scaduta.", "ja": "提案の有効期限が切れました。", "zh": "提案已过期。", "pt": "A proposta expirou."},
    "act.exec_disabled": {
        "en": "This edition only proposes; it never executes actions on GitHub.", "es": "Esta edición solo propone; nunca ejecuta acciones en GitHub.",
        "de": "Diese Edition schlägt nur vor; sie führt nie Aktionen auf GitHub aus.", "fr": "Cette édition ne fait que proposer ; elle n'exécute jamais d'action sur GitHub.",
        "it": "Questa edizione si limita a proporre; non esegue mai azioni su GitHub.", "ja": "このエディションは提案のみで、GitHub 上で操作を実行することはありません。",
        "zh": "此版本只提出建议，绝不会在 GitHub 上执行操作。", "pt": "Esta edição apenas propõe; nunca executa ações no GitHub."},
    "act.bad_state": {
        "en": "A proposal in state {state} cannot do that.", "es": "Una propuesta en estado {state} no puede hacer eso.",
        "de": "Ein Vorschlag im Zustand {state} kann das nicht.", "fr": "Une proposition à l'état {state} ne peut pas faire cela.",
        "it": "Una proposta nello stato {state} non può farlo.", "ja": "状態が {state} の提案ではこの操作はできません。",
        "zh": "处于 {state} 状态的提案无法执行此操作。", "pt": "Uma proposta no estado {state} não pode fazer isso."},
    "ai.disabled": {
        "en": "The assistant is off. Turn it on in the settings.", "es": "El asistente está apagado. Actívelo en los ajustes.",
        "de": "Der Assistent ist aus. Schalten Sie ihn in den Einstellungen ein.", "fr": "L'assistant est désactivé. Activez-le dans les réglages.",
        "it": "L'assistente è spento. Lo attivi nelle impostazioni.", "ja": "アシスタントはオフです。設定でオンにしてください。",
        "zh": "助手已关闭。请在设置中开启。", "pt": "O assistente está desligado. Ative-o nas definições."},
    "ai.airgapped_blocked": {
        "en": "Air-gapped mode: only providers on this machine or the local network are allowed ({host}).",
        "es": "Modo aislado: solo se permiten proveedores de este equipo o de la red local ({host}).",
        "de": "Isolierter Modus: Nur Anbieter auf diesem Rechner oder im lokalen Netz sind erlaubt ({host}).",
        "fr": "Mode isolé : seuls les fournisseurs de cette machine ou du réseau local sont autorisés ({host}).",
        "it": "Modalità isolata: sono ammessi solo provider su questa macchina o sulla rete locale ({host}).",
        "ja": "エアギャップモード: このマシンまたはローカルネットワーク上のプロバイダーのみ許可されます ({host})。",
        "zh": "隔离模式：仅允许本机或本地网络上的提供方（{host}）。",
        "pt": "Modo isolado: só são permitidos fornecedores nesta máquina ou na rede local ({host})."},
    "ai.no_provider": {
        "en": "No assistant provider is configured; the monitor works as before.", "es": "No hay proveedor de asistente configurado; el monitor funciona como antes.",
        "de": "Es ist kein Assistenten-Anbieter eingerichtet; der Monitor arbeitet wie bisher.", "fr": "Aucun fournisseur d'assistant n'est configuré ; le moniteur fonctionne comme avant.",
        "it": "Nessun provider dell'assistente è configurato; il monitor funziona come prima.", "ja": "アシスタントのプロバイダーが設定されていません。モニターはこれまでどおり動作します。",
        "zh": "未配置助手提供方；监视器照常工作。", "pt": "Não há fornecedor de assistente configurado; o monitor funciona como antes."},
    "ai.tool_denied": {
        "en": "The assistant may only read the monitor; {tool} is not allowed.", "es": "El asistente solo puede leer el monitor; {tool} no está permitido.",
        "de": "Der Assistent darf den Monitor nur lesen; {tool} ist nicht erlaubt.", "fr": "L'assistant ne peut que lire le moniteur ; {tool} n'est pas autorisé.",
        "it": "L'assistente può solo leggere il monitor; {tool} non è consentito.", "ja": "アシスタントはモニターの読み取りのみ可能です。{tool} は許可されていません。",
        "zh": "助手只能读取监视器；不允许使用 {tool}。", "pt": "O assistente só pode ler o monitor; {tool} não é permitido."},
}


def t(lang, key, **values):
    """The text of `key` in `lang` (English when it has none, the key itself when unknown); a missing or wrong placeholder never raises."""
    entry = CATALOGUE.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry["en"]
    try:
        return text.format(**values)
    except (KeyError, IndexError, ValueError):
        return text
