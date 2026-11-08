<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI.md) | [🇪🇸 Español](AI_spa.md) | [🇫🇷 Français](AI_fra.md) | [🇮🇹 Italiano](AI_ita.md) | [🇩🇪 Deutsch](AI_deu.md) | [🇨🇳 简体中文](AI_zho.md) | [🇯🇵 日本語](AI_jpn.md) | **🇵🇹 Português**

# O assistente de IA da sentinela

Opcional e **desligado por predefinição**. Um modelo de linguagem pode resumir o relatório diário, triar alertas, explicar um run falhado, redigir notas de versão e responder a uma pergunta sobre um repositório. Tudo o que escreve é mostrado como proposta por verificar.

## Fornecedores

- `ollama`: um modelo neste computador (só `127.0.0.1`; nada sai do computador).
- `openai-compatible`: qualquer serviço com um endpoint de chat ao estilo OpenAI. Serve também para o Gemini (o seu endpoint compatível com OpenAI) e para a própria OpenAI: defina `base_url`, `model` e o NOME da variável que guarda a chave.
- `anthropic`: a API Messages da Anthropic (`https://api.anthropic.com`, cabeçalhos `x-api-key` e `anthropic-version`). O modelo é você que o escolhe; nenhum vem incorporado.
- `copilot`: `gh copilot` com o seu próprio acesso ao GitHub (sem chave no monitor), só resposta de texto e sem ferramentas. Gasta pedidos premium do seu plano Copilot. Execute `gh copilot` uma vez à mão para instalar a CLI.
- A chave nunca é guardada: define-se o NOME de uma variável de ambiente. Os três fornecedores remotos ENVIAM dados dos seus repositórios a terceiros.


## O que pode ver

- Toda a entrada é limpa: carateres de controlo removidos, segredos ocultados por padrão, comprimento limitado, conteúdo entre delimitadores aleatórios e declarado não fiável. A resposta é cortada e as suas ligações neutralizadas.
- No separador Definições escolhe os tipos de evento que pode analisar (`build`, `codeql`, `report`), os repositórios que pode ver (vazio = os que o monitor vigia), o idioma das respostas, o limite diário de chamadas e os limites de tamanho. Um botão testa a ligação e a página mostra as chamadas de hoje.


## Propor e executar ações

- Nível 3 (`ai.actions.enabled`): um comando da resposta só é mantido se corresponder à LISTA FECHADA: `gh run rerun N --failed`, `gh run rerun N`, `gh issue close N` e `act -W FICHEIRO -j JOB` (este último só é mostrado). O comando mostrado é reconstruído a partir das peças verificadas, nunca copiado do modelo; o repositório e o número do run ou issue têm de ser já vigiados pelo monitor.
- Nível 4 (`ai.actions.execute`, interruptor próprio, desligado): cada proposta tem um botão de confirmar; uma janela mostra o comando inteiro e nada corre até aceitar. Corre com o seu próprio `gh`, sem shell, no máximo `ai.actions.max_per_hour` por hora, cada tentativa vai para o registo local mostrado pela página, e após duas falhas seguidas as ações ficam bloqueadas até as desbloquear.
- Fora da lista, de propósito: apagar ramos, fechar ou fundir pull requests, qualquer coisa sobre segredos ou definições.
