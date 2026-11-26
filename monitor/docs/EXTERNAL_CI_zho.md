<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTERNAL_CI.md) | [🇪🇸 Español](EXTERNAL_CI_spa.md) | [🇫🇷 Français](EXTERNAL_CI_fra.md) | [🇮🇹 Italiano](EXTERNAL_CI_ita.md) | [🇩🇪 Deutsch](EXTERNAL_CI_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](EXTERNAL_CI_jpn.md) | [🇵🇹 Português](EXTERNAL_CI_por.md)

# 外部 CI 来源(只读)

镜像到 GitHub 的仓库可能在别处构建。监视器可读取 Buildbot、GitLab CI、Jenkins 和 Azure Pipelines,并像 Actions 一样显示其失败。仅读取(GET),从不启动、取消或写入任何内容。适用于 Complete 和 Full 版本;默认关闭。

## 设置

开启 `external_ci.enabled`,并在 `external_ci.sources` 中每个来源写一行(设置 > 外部 CI)。`repo` 是结果显示时使用的名称。

```
buildbot;repo=my-mirror;url=https://buildbot.example.org;builders=linux+docs
gitlab;repo=my-mirror;url=https://gitlab.example.org;project=group/app;token_env=MY_GITLAB_VALUE
jenkins;repo=my-mirror;url=https://jenkins.example.org;job=folder/app;branch=main
azure;repo=my-mirror;url=https://dev.azure.com/my-org;project=my-project
```

## 失败、正常或降级

与 Actions 相同,以每个构建器、流水线或任务在其分支上最后一次完成的构建为准:合并请求以及已取消、已跳过和未知状态不参与判定。无响应、响应异常或缺少构建器的服务标记为**降级**,绝不标红;此前看到的失败保留并标记为过时。失败触发 ci.external.red(级别 `external_ci.alert.level`),像 Actions 失败一样计数、通知和静音;ci.external.degraded 仅为提示。静音它们不会静音任何安全告警。每个来源最多每 `external_ci.refresh_seconds`(不少于 300)读取一次,失败 `external_ci.breaker.failures` 次后降低频率。

## 安全

连接时检查地址:除非开启 `external_ci.allow_private_targets`,否则拒绝本机、私有网络和云元数据地址。不跟随重定向,也不跟随响应中的链接。响应受 `external_ci.max_bytes` 和 `external_ci.timeout_s` 限制。配置中从不写入凭据:`token_env` 只填环境变量名(GitLab:只读令牌;Jenkins:`user:token`;Azure:具有 Build 读取权限的个人令牌),且不会在无 TLS 时发往公网地址。不消耗 GitHub 配额。离线模式(`airgapped`)下不读取;`doctor --egress` 列出主机。

## 失败构建的日志

默认关闭(`external_ci.logs.enabled`)。只请求末尾部分,受 `external_ci.logs.max_kb` 和 `external_ci.logs.tail_lines` 限制,去除终端序列和控制字符,经脱敏后在内存保留 `external_ci.logs.keep_hours`。它是不可信文本,绝不作为指令交给 AI。脱敏无法识别所有密钥。

## 测试、状态、命令行

设置 > 外部 CI 提供**测试连接**:读取一次且不保存(`POST /api/external-ci/probe`)。哨兵区的 CI 标签页显示各来源;`GET /api/external-ci/status` 返回相同信息,`GET /api/external-ci/log` 返回一份日志。命令:`external-ci list`、`external-ci status`(有失败或降级时退出码 1)和 `external-ci probe --source "行"`。

## 尚未验证

四个适配器仅用模拟服务器测试(`tools/extci_fake_servers.py`)。Jenkins 和 Azure Pipelines 带有**实验性**标签(`external_ci.experimental`),需要 `external_ci.jenkins.enabled` / `external_ci.azure.enabled`。编写新适配器:在 `integrations/external_ci/extci_adapters.py` 中写函数 `(reader, source, cfg) -> (runs, missing)`,只通过 `reader` 读取。
