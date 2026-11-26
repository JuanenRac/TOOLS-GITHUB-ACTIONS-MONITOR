<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# GitHub Actions Monitor とは

[English](PRODUCT.md) · [Español](PRODUCT_spa.md) · [Français](PRODUCT_fra.md) · [Italiano](PRODUCT_ita.md) · [Deutsch](PRODUCT_deu.md) · [简体中文](PRODUCT_zho.md) · **日本語** · [Português](PRODUCT_por.md)

## 目的

個人や小さなチームに、自分のコンピューター上で、すべてのリポジトリの CI が本当に成功しているか、何がなぜ失敗したかを、各リポジトリを開かずに伝えます。

## 対象となる人

- 多数のリポジトリを持つ人（数個から数百個まで）。
- 画面や壁面ディスプレイを共有する小さなチーム。
- それらのリポジトリで作業し、プッシュ前に状態を読む必要がある AI ツール。

## 何であり、何でないか

自分のトークンまたは GitHub App で GitHub を読むローカルプログラムです。ホスト型サービスでも CI システムでもなく、GitHub の代わりにもなりません。観察が役割で、書き込みを行う少数の操作は有効にするまでオフです。

## 変わらないルール

- 追加パッケージは不要です。中核は Python 標準ライブラリです。
- 画面に見える設定が指定しない限り、何もコンピューターの外に出ません。テレメトリはありません。
- 確認していないものを成功として表示しません。
- GitHub やシステムに書き込む機能は初期状態でオフで、実行前に確認します。
- 画面とヘルプの文章はすべて 8 言語で用意されています。
- GPL-3.0-or-later。
