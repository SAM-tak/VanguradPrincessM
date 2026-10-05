# インスタンス操作のメソッド化

## 方針

対象インスタンスを第1引数に受け、その状態やライフサイクルを操作する処理は、対象の `def^` 内のメソッドとして表現する。
単に第1引数の型だけで機械的に分類せず、操作の主体を基準にする。
生成や、モジュール全体で共有するスタック・検索・スケジューラの操作は、その責務に応じてモジュール側に置く。

## Arena

`vp.arena.attach(a)` と `vp.arena.release(a)` を `a.attach()` と `a.release()` に変更。
定義は `Arena` の `def^` 内に移し、対象の参照は `self^` に統一する。旧形式のラッパーは残さない。
画面遷移・非同期ロード中断・勝利先読みテストの呼び出しも変更する。

`push`・`pop`・世代番号・全Arenaからの素材検索はスタック全体の操作なのでモジュール側に残す。
解放順序、スタックからの取り外し、世代更新のタイミングは変更しない。
従来通り `release()` は所有する素材を解放し、`pop()` が取り外しと世代更新を担当する。

コンパイルと既存の非同期ロード回帰テストで確認する。

## 全体への適用

Arenaに続き、以下の113処理をインスタンスメソッドに移した。旧公開関数のラッパーは残さず、内部呼び出し・main・既存テストも更新した。

| 型 | 移動した処理数 | 主な操作 |
|---|---:|---|
| Fighter | 57 | 技実行、コマンド入力、変数、攻撃・被弾、画像・音声、生成物 |
| cpu.Brain | 2 | reset、step |
| hud.Hud | 6 | restart、fightBegins、step、drawと内部操作 |
| preload.Load | 6 | add、character、victory、readyと素材要求 |
| resource.Batch / Job | 5 | request、ready、cancel / launch、finish |
| round.Round / Item | 9 | 状態遷移、取得マーク、描画項目の生成 / draw |
| script.Script | 7 | run、install、entry、showTime、layerIds、playersLayer、imagesFrom |
| select.Select / Side | 7 | カーソル・紹介画像・決定・描画 / confirmFlag |
| story.State | 5 | current、enter、advance、step、draw |
| stage.Stage | 2 | step、draw |
| title.Scene / Demos | 7 | タイトル更新・描画 / play、titleScreen |

`Script.run` と `Script.install` はスクリプトを主体とするので、第2引数だったScriptを受け手にし、Fighterを引数に残した。
`Fighter.level` と `Script.layers` は既存フィールドと重なるため、操作は `skillLevel()`、`layerIds()` とする。
`round.drawItem(item)` は `item.draw()` にした。
Sheetは既にメソッド中心のため維持した。Box・Command・入力Slotなどに不必要な操作は追加しない。

生成・全体のロード管理・描画専用ヘルパー・衝突の進行役など、対象インスタンスの責務に属さない関数は残す。
ワーカー間で渡す `scriptdata` のプレーンテーブルと、そのparse/linkはそのまま保持する。defインスタンス化すると転送方式に影響するため。

Fighterの子オブジェクト生成では、定義完成後に `Fighter.new` を呼ぶ小さな内部生成関数を使う。
メソッド内の `Fighter.new` はlet初期化前参照として拒否され、`def^.new` ではabstractなsheetの初期化検査が通らなかったため。
生成後の所有者・技・座標などの設定は `makeObject()` 内に保持する。

`gen_skills.py` も `me.show()` などの呼び出しを出力し、廃止したモジュール関数の別名を生成しない。
生成コードのコマンド登録には現行署名に必要なmodes/amountsを渡す（この下書き出力では空配列で従来の既定動作）。
Settings・I・S・SGとコマンド登録を含む生成サンプルをコンパイルして確認した。

## 検証結果

- mainと上記の生成サンプルをコンパイル。
- Python全22テスト成功。
- 既存のLÔVE回帰テスト8本すべて成功：async-flow、support-flow、story-flow、story-navigation、story-continue、selective-preload、victory-preload、attract-flow。
- サポート275入力、全10キャラの紹介、3難易度、コンティニューYES/NO、勝者10人×相手10人の勝利デモを確認。
- 非同期ロードの中断・再試行と、先読み済み素材の同期フォールバック0件を維持。
