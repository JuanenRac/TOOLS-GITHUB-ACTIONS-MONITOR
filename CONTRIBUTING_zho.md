# 为 GitHub Actions Monitor 做贡献

## 技术栈
- **语言**:Python 3.11 或更高;核心不需要任何包(终端视图 `bin/tui.py` 使用可选的 Rich,缺少时测试会跳过依赖它的部分)。
- **界面**:在 `127.0.0.1` 提供的本地网页(`monitor/assets/static/actions_monitor.html`),外加命令行工具。
- **数据源**:官方 GitHub 命令行客户端 `gh`(默认只读调用)。

## 准则
1. **先写测试**:提交 pull request 前 `python -m unittest discover -s monitor/tests` 必须通过。离线运行:测试从不调用 GitHub。要手动试用真实服务,请使用 `python tools/manual_check_live.py`。
2. **八种语言**:用户能读到的每段文字都在 `monitor/assets/locales/<lang>.json` 中(en、es、de、fr、it、ja、zh、pt=欧洲葡萄牙语)。新键要加入全部八个文件,测试会检查它们键相同。
3. **不留秘密**:默认监视器不保存令牌(向 `gh` 索取);唯一的可选令牌只存放在系统安全存储(`secretstore.py`)中。不要添加在其他地方读取、打印、记录或写入凭据的代码,也不要提交真实的 `actions_monitor.json`。
4. **默认安全**:任何写入 GitHub、运行程序、开放网络端口或向外发送数据的功能,默认关闭,在设置 > 高级中有自己的开关,要求自己的确认,并且除非开启网络模式否则只监听 `127.0.0.1`。此类功能须附带测试,证明没有开关、没有确认、没有令牌时会拒绝,且不会向日志泄露任何内容。
5. **小步前进**:每个 pull request 一项更改,并在 `CHANGELOG.md` 加上对应的一行。
6. **图片**:编辑 `docs/architecture.json` 或 `docs/structure.json`,再运行 `python tools/make_architecture.py` / `python tools/make_structure.py`;不要手工编辑 SVG。
7. **八种语言的更新日志**:`monitor/CHANGELOG.md` 的每条新条目都要在 `monitor/docs/CHANGELOG_<spa|deu|fra|ita|jpn|zho|por>.md` 中提供翻译(版本和章节相同;尚未翻译的条目在已翻译的提示下保留英文原文)。任何翻译缺少某个版本时,`python tools/make_help_index.py --check` 和发布检查都会失败。

## 每次发布后刷新状态看板

`.github/workflows/dashboard-dispatch.yml` 在 `CI` 工作流于 `main` 上变绿后运行(仅 push 事件)。如果维护者定义了可选的仓库密钥 `ECOSYSTEM_DASHBOARD_DISPATCH_TOKEN`,它会请求一个看板仓库刷新其版本表;没有该密钥时静默退出,没有任何权限,也从不更改或拖慢 CI。每次发布时 `electro-hobby-3d.project.json` 中的版本必须等于 `tool_version.py`;有测试检查。

- 帮助检查清单:每个新设置的设置帮助(`cfg.h.<键>`)、所改标签页的帮助、`monitor/docs/` 中的指南、八种语言、帮助索引(`python tools/make_help_index.py`)和更新日志。
