# TechnicalDocuments

技術検証結果・決定事項のメモ置き場。1トピック1ファイル。

ファイル名: `NNNN-topic.md`（連番 + 英小文字ケバブ）。

各メモの構成:

- **日付** — 記録日
- **状況** — 何が起きたか / 何を調べたか
- **原因・結果** — 確認できた事実
- **決定** — 採用した方針とその理由
- **移植への影響** — lhat-love 実装側で気をつけること

## 一覧

- [0001-utf8-locale-launch-failure.md](0001-utf8-locale-launch-failure.md) — UTF-8 システムロケールで原作 exe が起動しない問題と対処（外部マニフェストで解決）
- [0002-fm2k-file-format-survey.md](0002-fm2k-file-format-survey.md) — FM2K データフォーマットの初期調査と既存資料
- [0003-asset-pipeline-decision.md](0003-asset-pipeline-decision.md) — KGT は移行元のみ。png/ogg/LTON へ一度だけ変換する方針
- [0004-skills-as-lhat-code.md](0004-skills-as-lhat-code.md) — 技を L^ のコルーチンとして書く見本（ゆい）
- [0005-skill-code-generation.md](0005-skill-code-generation.md) — FM2K のブロック列から技の L^ コードを生成する
- [0006-engine-built-in-behaviour.md](0006-engine-built-in-behaviour.md) — エンジン側の挙動（ジャンプ・落下・着地、攻撃の割り当て）
- [0007-stage-and-commands.md](0007-stage-and-commands.md) — ステージ（レイヤー・多重スクロール・透過色）、コマンド表、キャンセル、ヒット判定
- [0008-hit-reactions.md](0008-hit-reactions.md) — 相手の反応（反応番号の 3 段の表、ガードの規則＝下段・中段、ダメージ、ヒットストップ）
- [0009-objects.md](0009-objects.md) — オブジェクト（O）: ボイス・エフェクト・ヒットスパーク・飛び道具、変数の共有範囲、影、parent＝生成元への追従
- [0010-gauges-and-hud.md](0010-gauges-and-hud.md) — ゲージ（体力・必殺、GP / GL / GS）と HUD（システムの枠とゲージ、キャラの開始時技が出す HUD）
- [0011-measured-in-the-original.md](0011-measured-in-the-original.md) — 原作のメモリから測った値（地面 920、壁、画面の端とカメラ、開始位置、移動は速度が先、I の待ちは足し算）
- [0012-skills-as-data.md](0012-skills-as-data.md) — 技はデータ（script.lton）にして src/script.lh で解釈実行（0005 の L^ 生成を置き換え）。形式と確認結果
- [0013-round-flow.md](0013-round-flow.md) — ラウンドの流れ（VS 画面・READY / FIGHT・KO・勝ちマーク）とシステムのオブジェクトの規則
- [0014-music-loop.md](0014-music-loop.md) — BGM のループ（ループポイントなし、ファイル全体の単純ループ）
- [0015-vs-mode-loop.md](0015-vs-mode-loop.md) — 対戦モードのループ（キャラ選択画面の仕組み、試合 → 選択へ戻る）
- [0016-opening-and-title.md](0016-opening-and-title.md) — 起動からキャラ選択まで（デモの割り当て、オープニング、タイトル画面）
- [0017-distribution-build.md](0017-distribution-build.md) — 配布ビルド（VM のみのエンジン + fused）の手順と、エンジン側の生成物の作り直し
- [0018-hit-combo-display.md](0018-hit-combo-display.md) — コンボ表示（HIT COMBO）の素材・原作で測った位置と出方・実装
- [0019-data-patches.md](0019-data-patches.md) — 原作データの差し替え（変換時のパッチ `tools/fm2k_convert/patches/`）、キャラ選択の幕を手前に
- [0020-shared-assets.md](0020-shared-assets.md) — キャラ間で同じ png / wav を assets/shared に纏める（share_assets.py、エンジンは .lton の項目から読む）
- [0021-indexed-images-as-dds.md](0021-indexed-images-as-dds.md) — パレット画像を非圧縮 R8 の DDS で持つ（r8 テクスチャ、VRAM 1/4）。共有の判定は画素の鍵で
- [0022-character-names.md](0022-character-names.md) — キャラの内部名 → 正式名（えり・サキ・はるか・あやね）、未使用キャラ new1 / 新2 を変換しない
- [0023-resource-arena.md](0023-resource-arena.md) — 場面ごとのアリーナのスタックでテクスチャ・音をまとめて dispose。キャラ選択の顔グラ先読み（portrait.lton）と試合前の 2 キャラ先読み
