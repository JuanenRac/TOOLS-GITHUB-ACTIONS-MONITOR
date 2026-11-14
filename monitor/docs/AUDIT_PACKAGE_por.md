<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_PACKAGE.md) | [🇪🇸 Español](AUDIT_PACKAGE_spa.md) | [🇫🇷 Français](AUDIT_PACKAGE_fra.md) | [🇮🇹 Italiano](AUDIT_PACKAGE_ita.md) | [🇩🇪 Deutsch](AUDIT_PACKAGE_deu.md) | [🇨🇳 简体中文](AUDIT_PACKAGE_zho.md) | [🇯🇵 日本語](AUDIT_PACKAGE_jpn.md) | **🇵🇹 Português**

# Pacote para o auditor

O que um auditor precisa para verificar o modo de equipa, a exposição na rede e o tratamento de segredos desta ferramenta: uma lista de verificação, as conclusões de revisões anteriores com a sua correção e o teste que a mantém, como executar os testes e o que se sabe que falta.

## Lista de verificação de segurança do modo de equipa

- O modo de equipa (`auth.enabled`) está desligado por omissão; ative-o apenas atrás de HTTPS ou de um proxy de confiança (`listen.trusted_proxy`).
- Com o modo de equipa ativo e a rede aberta, o monitor não arranca antes de existir o primeiro administrador.
- Até lá só entra o próprio computador (o primeiro administrador é criado aí).
- Os tokens para scripts (`auth.allow_bearer`) estão desligados por omissão; uma sessão precisa do token CSRF para escrever.
- O processo de cada conta responde apenas ao seu supervisor (uma chave recebida no arranque).
- Nenhum segredo é escrito no registo nem nas respostas da API; o ficheiro de definições é guardado sob um bloqueio.
- Todo o pedido que sai do monitor (avisos, OpenTelemetry, exportadores de runners) obedece à mesma regra: nenhum endereço privado nem redireção para um.

## Conclusões, correções e testes

| Conclusão | Correção | Teste |
|---|---|---|
| Com o modo de equipa e sem utilizadores, todas as rotas estavam abertas à rede | Só o próprio computador entra até existir o primeiro administrador, e o modo de rede não arranca sem um | `test_184_audit_auth.py::FirstAdministratorWindow, test_185_bootstrap_start.py` |
| O processo de uma conta saltava as verificações do modo de equipa | Pede a chave do seu supervisor em cada pedido | `test_184_audit_auth.py::ChildAnswersOnlyToItsSupervisor` |
| Guardar as definições continuava sem o bloqueio do ficheiro após um tempo limite | O guardar é recusado com uma mensagem se o bloqueio ficar tomado dez segundos | `test_184_audit_hardening.py::ConfigurationLock` |
| O comando da sentinela podia ser uma shell com argumentos | O comando é uma lista cuja primeira palavra é o caminho completo de um programa que não é uma shell, sem caracteres de controlo | `test_184_audit_hardening.py::NotifyCommand` |
| Os tokens para scripts (bearer) estavam ativos por omissão | Desligados por omissão; só um true verdadeiro os ativa | `test_184_audit_hardening.py::ScriptTokens` |
| O feed para as IAs era partilhado entre contas, e atualização, confirmação e limite de avisos podiam ultrapassar-se | Um feed por conta; atualização, confirmação e estado tomam o mesmo bloqueio; o limite é reservado num passo com bloqueio | `test_184_audit_feed.py (OneStepAtATime, CapOfTheNotices)` |
| A pausa do gancho de uma ferramenta de IA não era reservada num passo; um exportador de runner podia redirecionar o monitor; as chamadas ao GitHub que não voltam acumulavam-se | A pausa é mantida com bloqueio; as redireções são verificadas e limitadas; as chamadas abandonadas são contadas e limitadas (`watchdog_max_abandoned`) | `test_184_audit_robustness.py (HookCooldown, Exporter, AbandonedCalls)` |
| Um nome terminado em quebra de linha passava as verificações de ids, repositórios e chaves | Toda a verificação termina no fim do texto (`\Z`) | `test_184_audit_anchors.py` |
| A exportação OpenTelemetry não obedecia à regra dos pedidos de saída; o proxy não era apresentado como fronteira de confiança; o escape da página não tinha teste | A exportação passa pela mesma guarda (sem endereço privado nem redireção); a fronteira está documentada na ajuda; um teste mantém com escape cada texto da API | `test_184_audit_network.py (Collector, ProxyIsAFrontierOfTrust, PageEscaping)` |
| Dois monitores podiam escutar na mesma porta; o openssl do Git for Windows não era encontrado; as falhas engolidas de propósito não deixavam rasto da origem | A porta é tomada em exclusivo e um segundo monitor recusa-se a arrancar; o openssl é procurado onde o Git for Windows o guarda; cada falha engolida escreve uma linha com o seu tipo e lugar | `test_185_startup.py (OnePerPort, WhereIsOpenssl), test_185_degraded.py` |
| As execuções sem duração (lidas por GraphQL) faziam a sentinela falhar em cada ciclo | Uma duração em falta conta como zero | `test_186_unfinished_rows.py` |

## Como executar os testes

A partir da pasta `monitor/`: `python -m unittest discover -s tests`. Os testes não precisam de rede nem de token do GitHub. Os testes de navegador correm se houver Edge, Chrome ou Chromium (ou com `MONITOR_BROWSER_TESTS=1`). Os ficheiros da tabela estão em `monitor/tests/`.

## Limites conhecidos

- O proxy do ambiente (`network.use_proxy`, desligado por omissão) resolve os nomes por conta própria: a verificação do nome acontece antes. A garantia forte tem de vir da rede (uma firewall que recuse endereços privados).
- O Windows não consegue tornar um ficheiro privado só com permissões: os segredos são cifrados com a chave do utilizador onde o sistema o permite.
- Os testes não provam nada sobre um GitHub real, um proxy real ou um servidor de correio real: usam duplos locais.
