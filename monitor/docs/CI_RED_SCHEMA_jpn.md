<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_SCHEMA.md) | [🇪🇸 Español](CI_RED_SCHEMA_spa.md) | [🇫🇷 Français](CI_RED_SCHEMA_fra.md) | [🇮🇹 Italiano](CI_RED_SCHEMA_ita.md) | [🇩🇪 Deutsch](CI_RED_SCHEMA_deu.md) | [🇨🇳 简体中文](CI_RED_SCHEMA_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](CI_RED_SCHEMA_por.md)

# ci_red.json - スキーマ 2（安定した契約）

`ci_red.json` は、モニターが書き出すスナップショット（アトミックに、既定ではモニターのすぐ隣へ）です。ダッシュボード、スクリプト、通知フックなど、あらゆる利用側が、モニターにも GitHub にも問い合わせることなく CI の状態を読み取れます。形式は**安定しています。フィールドは追加されるだけで、名前の変更や削除は決して行われません**。
`.get()` で読み取り、知らないフィールドは無視してください。

書き出し先は `actions_monitor.json` で設定します。

| キー（`sentinel.`） | 意味 |
|---|---|
| `ci_red_file` | `""` = モニターの隣の `ci_red.json`（既定）、`"off"` = 書き出さない、パス = そのパスに書き出す（相対パスはモニターのフォルダーが基準。D: ドライブ、UNC パス、実行中のシステムが使えないドライブは拒否される） |
| `ci_red_audit_copy` | `true` にすると、監査フォルダーが存在する場合はそこにもコピーする |

## 構造

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

* `complete` は、センチネルがまだ読み込み中の間は `false` です。その場合、見当たらないリポジトリを緑とみなさないでください。
* `signature_verified` は `true`、`false`、または文字列 `"unknown"` のいずれかです（推測は決して行いません。このツールが確認できない形式は `"unknown"` になります）。
* `pending_sign*` フィールドは**ローカルの署名側**を表すもので、ご自身のローカルツール向けです。公開の利用側は無視してください。

## 「赤」の規則（どこでも同じ定義）

**各ワークフローのデフォルトブランチで最後に完了した実行**を見ます。その結論が `failure`、`timed_out`、`startup_failure`、`action_required`（承認待ち）のいずれかであれば赤です。`cancelled`、`skipped`、`neutral`、`stale` は何も示さないため無視されます。
署名状態における「緑」も、同じ実行の一覧を用います。ワークフローの実行からこの規則を再計算する利用側は、モニターと一致させるために、まったく同じこの定義を使わなければなりません。

## 公開は別の、明示的な手順です

**決定事項：この PC は `ci_red.json` を公開せず、`pending_sign` を含む署名側のいかなる部分も、リポジトリ、ダッシュボード、その他のサービスに公開しません。**
ファイルはマシン上にとどまります（`ci_red_audit_copy` が有効な場合はローカルの監査フォルダーにも置かれます）。公開ダッシュボードは、上記の規則を使って公開されているワークフローの実行から赤の一覧を再計算するか、次に説明するエクスポートを使う必要があります。このエクスポートには署名状態が含まれることはありません。

モニターのどの機能も、このファイルをリポジトリに公開しません。公開ダッシュボードが赤の一覧を必要とする場合は、公開されている実行データから規則を再計算させるか、機密でない部分をご自身でエクスポートしてください。

```
python3 read_report.py --export-status DIR
```

これは、指定したフォルダーに `ci_status_public.json` と `ci_status_public.md` を書き出し、書き出されるのは赤のワークフローの一覧**のみ**です（リポジトリ、エコシステム、ワークフロー、結論、開始時刻、連続回数、実行へのリンク）。署名状態、キー名、ローカルパス、コマンドは含まれません。このツールがコミットやプッシュを行うことはありません。そのフォルダーをその後どうするかは、あなた次第です。

`python3 read_report.py --export-sign-queue FILE`（`.json` または `.csv`）は、実行すべきローカルのコマンドを正確に含んだ、全体の署名キューを書き出します。このファイルはモニターを動かしている PC 向けのもので、その旨がファイル内にも記されています。

赤い各ワークフローの任意フィールド `ai_hint`(1.6.4 で追加): `{"class": "real|transient", "cause", "action"}`。AIやスクリプト向けです。`.get()` で読む利用側は無視できます。
