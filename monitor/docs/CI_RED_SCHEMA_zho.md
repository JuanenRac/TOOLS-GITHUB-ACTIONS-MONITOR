<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_SCHEMA.md) | [🇪🇸 Español](CI_RED_SCHEMA_spa.md) | [🇫🇷 Français](CI_RED_SCHEMA_fra.md) | [🇮🇹 Italiano](CI_RED_SCHEMA_ita.md) | [🇩🇪 Deutsch](CI_RED_SCHEMA_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](CI_RED_SCHEMA_jpn.md) | [🇵🇹 Português](CI_RED_SCHEMA_por.md)

# ci_red.json - 模式 2（稳定契约）

`ci_red.json` 是监视器写出的快照（以原子方式写入，默认位于监视器自身旁边），任何使用方都可以据此读取 CI 状态，而无需询问监视器或 GitHub：仪表板、脚本、通知钩子均可。该格式是**稳定的：字段只会新增，绝不会重命名或删除**。
请使用 `.get()` 读取；忽略您不认识的字段。

写出位置在 `actions_monitor.json` 中设置：

| 键（`sentinel.`） | 含义 |
|---|---|
| `ci_red_file` | `""` = 监视器旁边的 `ci_red.json`（默认）；`"off"` = 不写出；路径 = 写到该处（相对路径相对于监视器文件夹；D: 盘、UNC 路径或运行中的系统无法使用的驱动器会被拒绝） |
| `ci_red_audit_copy` | `true` 时，若审计文件夹存在，还会将其复制到该文件夹 |

## 结构

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

* 哨兵仍在加载时，`complete` 为 `false`：此时请勿把缺失的仓库当作绿色。
* `signature_verified` 为 `true`、`false` 或字符串 `"unknown"`（绝不猜测：本工具无法检查的格式一律为 `"unknown"`）。
* `pending_sign*` 字段描述**本地签名一侧**，仅供您自己的本地工具使用。公开的使用方应忽略它们。

## “红色”的规则（处处只有一个定义）

查看**每个工作流在默认分支上最近一次完成的运行**。当其结论为 `failure`、`timed_out`、`startup_failure` 或 `action_required`（等待批准）时，即为红色。`cancelled`、`skipped`、`neutral` 和 `stale` 不说明任何问题，会被忽略。
签名状态中的“绿色”使用同一份运行列表。若使用方根据工作流运行重新计算该规则，必须使用与此完全相同的定义，才能与监视器保持一致。

## 发布是单独且明确的一步

**决定：这台 PC 不发布 `ci_red.json`，也不会把 `pending_sign` 或签名一侧的任何其他部分发布到仓库、仪表板或任何服务。**
该文件保留在本机（当 `ci_red_audit_copy` 开启时，还会放在本地审计文件夹中）。公开的仪表板必须根据公开的工作流运行，按上述规则重新计算红色列表，或使用下面介绍的导出功能，该导出绝不包含签名状态。

监视器中没有任何功能会把此文件发布到仓库。如果公开的仪表板需要红色列表，要么让它根据公开的运行数据重新计算该规则，要么自行导出其中不敏感的部分：

```
python3 read_report.py --export-status DIR
```

这会在您指定的文件夹中写入 `ci_status_public.json` 和 `ci_status_public.md`，且**只**包含红色工作流的列表（仓库、生态系统、工作流、结论、起始时间、连续次数、运行链接）。不含签名状态、密钥名称、本地路径或命令。该工具绝不会提交或推送；之后如何处置该文件夹由您决定。

`python3 read_report.py --export-sign-queue FILE`（`.json` 或 `.csv`）会写出全局签名队列以及确切的本地命令。该文件仅供运行监视器的那台 PC 使用，并在文件内部注明了这一点。
