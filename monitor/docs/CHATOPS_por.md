<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CHATOPS.md) | [🇪🇸 Español](CHATOPS_spa.md) | [🇫🇷 Français](CHATOPS_fra.md) | [🇮🇹 Italiano](CHATOPS_ita.md) | [🇩🇪 Deutsch](CHATOPS_deu.md) | [🇨🇳 简体中文](CHATOPS_zho.md) | [🇯🇵 日本語](CHATOPS_jpn.md) | **🇵🇹 Português**

# Comandos de chat (Slack e Discord)

Opcional, **desligado por defeito**. Permite perguntar ao monitor, a partir de um canal do Slack ou do Discord, por um estado breve: quantos repositórios estão a vermelho, os alertas abertos, a fila e a pontuação. É **só de leitura**.

## O que faz (e o que nunca faz)

- Os comandos são uma lista fechada: `help`, `status`, `alerts`, `red`, `queue` e `score`. Tudo o resto recebe «Não conheço esse comando». `chatops.allowed_words` só pode reduzir a lista.
- Um comando lê o que o monitor já tem (o último ciclo, os alertas, a pontuação). Nunca escreve no GitHub, nunca executa uma ação, nunca altera uma definição e nunca lê um segredo; não existe um comando para isso e não se pode acrescentar nenhum a partir do chat.
- A resposta só é vista por quem perguntou, não menciona ninguém e não leva ligações exceto uma: com `chatops.links` ligado (por defeito), o endereço de um repositório (`https://<host>/<proprietário>/<repositório>`, verificado) junto de um nome mostrado tal como é. Todo o texto que vem do GitHub (o nome de um repositório ou de um workflow) é limpo, cortado e escapado para a plataforma.
- Cada comando que chega ao monitor deixa uma linha no registo de ações (`chatops_command`) com os ids do chat, nunca o texto do pedido.

## Segurança

- Desligado até que `chatops.enabled` e o interruptor da plataforma (`chatops.slack.enabled`, `chatops.discord.enabled`) estejam ligados **e** a prova esteja no ambiente. As definições guardam só o NOME da variável (`chatops.slack.signing_secret_env`, `chatops.discord.public_key_env`), nunca o seu valor; o valor nunca é escrito, mostrado nem registado.
- Slack: cada pedido tem de levar `X-Slack-Signature: v0=<hmac>`, o HMAC-SHA256 de `v0:<marca de tempo>:<corpo>` feito com o segredo de assinatura, e `X-Slack-Request-Timestamp` não mais antigo do que `chatops.max_age_seconds` (cinco minutos no máximo). A comparação demora o mesmo tempo seja qual for a assinatura.
- Discord: cada pedido tem de levar `X-Signature-Ed25519` e `X-Signature-Timestamp`: uma assinatura Ed25519 da marca de tempo seguida do corpo, verificada com a chave pública da sua aplicação (RFC 8032, biblioteca padrão; nada é aceite sem a verificação).
- Uma assinatura má, antiga ou do futuro recebe `401` e nada do corpo é examinado. Uma assinatura já aceite nunca é aceite outra vez. Um corpo com mais de 16 KB recebe `413`. Um endereço pode fazer 120 pedidos por minuto.
- **As listas são obrigatórias**: `chatops.allowed_teams`, `chatops.allowed_channels` e `chatops.allowed_users`. Sem nenhuma preenchida, nenhum comando é executado (o desafio da plataforma continua a ser respondido para poder concluir a configuração). Uma lista com entradas tem de conter a equipa, o canal ou o utilizador do pedido.
- Limites por minuto: `chatops.rate_per_user_per_minute`, `chatops.rate_per_channel_per_minute` e `chatops.rate_per_minute`. A resposta tem de chegar em 3 segundos: o monitor responde a partir da memória e, se fosse mais lento, diz que está ocupado.
- As duas rotas (`/api/chatops/slack`, `/api/chatops/discord`) não pedem o token de acesso do modo de rede, porque uma plataforma não o pode enviar: a assinatura é a sua prova, tal como no webhook de entrada. O monitor continua a escutar só em `127.0.0.1` enquanto não abrir o modo de rede; as plataformas só o alcançam por um endereço HTTPS que monta de propósito (um túnel ou um proxy inverso; a ferramenta nunca abre nenhum). Publique por aí apenas `/api/chatops/`.

## Os comandos

| Comando | Resposta |
| --- | --- |
| `help` | a lista de comandos |
| `status` | repositórios a vermelho, bloqueados, à espera, a verde e inativos, e os alertas abertos |
| `alerts` | os alertas abertos (nível, código e repositório), até `chatops.max_rows` |
| `red` | os workflows a vermelho com o tempo que levam assim, até `chatops.max_rows` |
| `queue` | em execução, em fila, a aguardar aprovação e minutos usados em 24 horas |
| `score` | a pontuação, a sua letra e a sua variação |

`chatops.show_repo_names` decide os nomes: `all` (por defeito: todos os nomes, também dos repositórios privados), `public` (um repositório privado passa a `private-N` e os seus workflows não são nomeados) ou `none`. **Risco de `all`:** os nomes de repositórios e workflows privados chegam a todos os canais e utilizadores que as suas listas permitam. Por isso as listas são obrigatórias e cada lista com entradas tem de coincidir (equipa, canal e utilizador em conjunto). Escolha `public` ou `none` se o canal for mais amplo do que as pessoas que podem conhecer esses nomes.

## Slack, passo a passo

1. Abra api.slack.com/apps > Create New App > From scratch. Dê-lhe um nome e escolha o seu workspace.
2. Slash Commands > Create New Command: comando `/monitor`, **Request URL** `https://<o seu endereço público>/api/chatops/slack`, uma descrição breve. Não é preciso nenhum scope de bot.
3. Basic Information > App Credentials > **Signing Secret**: copie-o e entregue-o ao monitor pelo ambiente, nunca pelo ficheiro: `$env:MONITOR_SLACK_SIGNING_SECRET = "<signing secret>"` no PowerShell antes de arrancar o monitor, `export MONITOR_SLACK_SIGNING_SECRET=...` numa shell, uma entrada de ambiente ou um ficheiro de segredo num serviço ou num contentor.
4. Instale a aplicação no workspace (Install App).
5. Preencha as listas: o id da sua equipa (começa por `T`), o id do canal (abra o canal, os detalhes, o id no fim: `C...`) e o seu id de membro (o seu perfil > Copy member ID: `U...`). Ponha-os em Definições > Comandos de chat, ou `"chatops": {"allowed_channels": ["C0123456789"]}` em `actions_monitor.json`.
6. Ligue Comandos de chat e Slack e reinicie o monitor.

## Discord, passo a passo

1. Abra discord.com/developers/applications > New Application. Em General Information copie a **Public Key** (64 caracteres hexadecimais) e entregue-a ao monitor pelo ambiente: `$env:MONITOR_DISCORD_PUBLIC_KEY = "<chave pública>"` no PowerShell, `export MONITOR_DISCORD_PUBLIC_KEY=...` numa shell.
2. Preencha as listas, ligue Comandos de chat e Discord (Definições > Comandos de chat) e reinicie o monitor. Faça-o **antes** do passo seguinte: o Discord envia um teste assinado quando guarda o endereço e recusa-o se o monitor não responder.
3. General Information > **Interactions Endpoint URL**: `https://<o seu endereço público>/api/chatops/discord`, e Save.
4. Registe o comando uma vez com a sua própria ferramenta (a API do Discord, `POST /applications/<id da aplicação>/commands`) com este corpo:

```json
{
  "name": "monitor",
  "description": "Read only status of the GitHub Actions Monitor",
  "type": 1,
  "options": [{"name": "command", "description": "help, status, alerts, red, queue or score", "type": 3, "required": false,
               "choices": [{"name": "help", "value": "help"}, {"name": "status", "value": "status"}, {"name": "alerts", "value": "alerts"}, {"name": "red", "value": "red"}, {"name": "queue", "value": "queue"}, {"name": "score", "value": "score"}]}]
}
```

5. Convide a aplicação apenas com o scope `applications.commands` (OAuth2 > URL Generator); não é preciso nenhuma permissão de bot. Ids: no Discord ative o Modo de programador (Avançado) e use Copiar ID no servidor, no canal e no seu utilizador.

## Experimentar

Num canal permitido escreva `/monitor help` (Slack) ou `/monitor command:status` (Discord). Outras respostas:

| O que vê | Significado |
| --- | --- |
| nada, ou «não respondeu» | o endereço não é alcançável, o monitor está desligado, ou respondeu `401` (segredo ou chave errados, ou um relógio desfasado mais de cinco minutos) |
| «Este comando não está disponível aqui.» | a equipa, o canal ou o utilizador não está nas listas |
| «Demasiados comandos.» | um dos três limites por minuto |
| «O monitor ainda não leu o GitHub.» | o primeiro ciclo não terminou |
