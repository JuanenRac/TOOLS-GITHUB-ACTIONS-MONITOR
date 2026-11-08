# Política de segurança

## Comunicar uma vulnerabilidade

Comunique os problemas de segurança em privado para `electrohobby3d@gmail.com` (ou com um aviso de segurança privado deste repositório) e não abra uma issue pública.
Os relatórios úteis são: uma forma de chegar à página web local a partir de outra máquina, uma forma de fazer o monitor escrever fora da sua própria pasta, uma forma de ler um token
ou um ficheiro privado através da página ou do endpoint de métricas, ou uma injeção através do nome de um repositório, de um workflow ou de uma linha de registo.

## Pontos de conceção em que pode confiar
- A página web e o endpoint opcional de métricas escutam apenas em `127.0.0.1` e recusam pedidos cujo `Host` ou `Origin` não seja local. O modo rede opcional (desligado por defeito) acrescenta um token de acesso em cada pedido, uma lista de nomes de máquina aceites e um aviso persistente.
- Por defeito o monitor não guarda nem mostra tokens; chama o seu próprio cliente `gh` autenticado. O token opcional guardado pelo monitor vive no cofre seguro do sistema e nunca é escrito numa definição, num registo nem numa resposta.
- Tudo o que escreve no GitHub ou executa um programa está desligado por defeito, cada ação é confirmada à parte com um token de uso único, e o assistente de IA não pode iniciar nenhuma.
- A página de configuração só escreve uma lista fixa de chaves, validadas, depois de guardar uma cópia de segurança.
