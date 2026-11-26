<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# GitHub Actions Monitor: o que é

[English](PRODUCT.md) · [Español](PRODUCT_spa.md) · [Français](PRODUCT_fra.md) · [Italiano](PRODUCT_ita.md) · [Deutsch](PRODUCT_deu.md) · [简体中文](PRODUCT_zho.md) · [日本語](PRODUCT_jpn.md) · **Português**

## Finalidade

Dizer a uma pessoa ou a uma pequena equipa, no próprio computador, se a CI de todos os repositórios está realmente verde, o que falhou e porquê, sem abrir cada repositório.

## Para quem

- Donos de muitos repositórios (de alguns a várias centenas).
- Pequenas equipas que partilham um ecrã ou um painel de parede.
- Ferramentas de IA que trabalham nesses repositórios e precisam de ler o estado antes de enviar alterações.

## O que é e o que não é

É um programa local que lê o GitHub com o seu próprio token ou GitHub App. Não é um serviço alojado, não é um sistema de CI e não substitui o GitHub: observa, e as poucas ações que escrevem estão desligadas até as ligar.

## Regras duradouras

- Não é preciso nenhum pacote: o núcleo é a biblioteca padrão do Python.
- Nada sai do computador a não ser que uma definição visível o diga; não há telemetria.
- O que não foi verificado nunca aparece a verde.
- Tudo o que escreve no GitHub ou no sistema está desligado por omissão e pergunta antes de agir.
- Cada texto da interface e da ajuda existe em oito idiomas.
- GPL-3.0-or-later.
