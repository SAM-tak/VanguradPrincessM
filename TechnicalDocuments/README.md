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
- [0024-select-input-reset.md](0024-select-input-reset.md) — 試合中の上下入力フラグを消費し、キャラ選択へ戻った際のカーソル移動を防ぐ
- [0025-round-mark-lifecycle.md](0025-round-mark-lifecycle.md) — 決着時は新規取得マークだけ更新し、次ラウンド開始時は全マークの表示を再開する
- [0026-custom-opening.md](0026-custom-opening.md) — タイトル素材を直接使う35秒の演出、文字のフェードと最終行の中央停止、二段階のスキップと入力待ち
- [0027-escape-navigation.md](0027-escape-navigation.md) — ESCで前の画面へ戻る。タイトルでは終了、試合中は無処理
- [0028-async-loading.md](0028-async-loading.md) — 素材とLTONの非同期読み込み、所有権移譲、キャンセルと専用ワーカー1本によるコア競合の回避
- [0029-core-member-race-repro.md](0029-core-member-race-repro.md) — LÖVE不要の20行で複数ワーカー間の誤読を再現。言語コアへの修正依頼と比較結果
- [0030-story-flow-survey.md](0030-story-flow-survey.md) — ストーリー用キャラセレ、開始時スクリプトによる難易度・紹介画面、イベント列と未確認点
- [0031-story-mode.md](0031-story-mode.md) — だみー対戦を使わない難易度・紹介・ロード、原作ルートの抽出、CPU戦と検証範囲
- [0032-gamepad-and-two-player-input.md](0032-gamepad-and-two-player-input.md) — パッド接続と操作割り当て、独立した2P選択・対戦入力、デバッグキーの移動
- [0033-battle-pause.md](0033-battle-pause.md) — ESC／Startでの停止・再開と原作の全画面操作説明画像
- [0034-shared-image-ownership.md](0034-shared-image-ownership.md) — ゆい専用15枚の共有解除、共有済み素材への所有者訂正の適用
- [0035-cooldown-icon-sharing.md](0035-cooldown-icon-sharing.md) — サポート禁止アイコン11点を指定の共有画像へ統一、パレット番号差と明示的置換
- [0036-support-identification.md](0036-support-identification.md) — 5種類のサポートと通常25アクションの抽出、くるみ専用の要求93、ルナ・ヒルダの入力差分
- [0037-shared-support-definitions.md](0037-shared-support-definitions.md) — ゆい基準のサポート定義・素材の独立化、くるみの追加口、D入力と非同期読み込み
- [0038-support-media-folders.md](0038-support-media-folders.md) — サポート専用画像572点・音声14点の各サポート配下への移動、全素材一覧の参照更新
- [0039-selected-support-preload.md](0039-selected-support-preload.md) — 選択サポートの画像・音声だけを先読み、CPUサポートの事前確定、勝利デモの一括読み込み調査
- [0040-victory-demo-preload.md](0040-victory-demo-preload.md) — 勝者別に事前生成した素材一覧で勝利デモを先読み、相手別台詞と乱数候補は保持
- [0041-mode-confirm-transition.md](0041-mode-confirm-transition.md) — モード決定時に決定音と暗転、その後キャラセレをロード。キャラセレ冒頭音は抑止
- [0042-title-attract-mode.md](0042-title-attract-mode.md) — タイトル音楽終了／無音30秒から最高強度CPUデモ、60秒／2本先取でループ、ボタンでモードセレクト
- [0043-demo-character-name.md](0043-demo-character-name.md) — キャラセレを通らないデモ対戦で1P番号が未設定になる問題、ラウンド開始時に両側を設定
- [0044-support-helper-isolation.md](0044-support-helper-isolation.md) — サポート補助54技の共通側への抽出、えりの音声誤発火修正、参照スロットと中間データの位置付け
- [0045-support-skill-namespaces.md](0045-support-skill-namespaces.md) — サポート技を専用skillsへ移し、キャラ側の参照スロットを撤去。独立番号・くるみの差分・配布対象
- [0046-versioned-game-data.md](0046-versioned-game-data.md) — 素材はassets、ゲーム用LTONはGit管理するdataへ分離。変換・非同期ロード・配布の対応
- [0047-instance-methods.md](0047-instance-methods.md) — インスタンス操作をdef内のメソッドへ整理する方針、Arenaのattach/releaseから適用
- [0048-combat-hit-guard-shake.md](0048-combat-hit-guard-shake.md) — 持続判定の重複ヒット抑止、連続ガード、EB揺れ指定の復元と描画への適用
- [0049-melt-shot-target-filters.md](0049-melt-shot-target-filters.md) — メルトショットの過剰追撃、FAのやられ／ガード反応・地上／空中の対象除外
- [0050-yui-super-finisher.md](0050-yui-super-finisher.md) — ゆい超必殺技の最終段、後付けDSの命中通知と全FA削除時の判定群終了
- [0051-air-push-and-landing-audit.md](0051-air-push-and-landing-audit.md) — FDに従った空中との押し合い、2C→超必殺技の実判定テスト、斜めジャンプAの着地236ケース
- [0052-support-facing-and-shell-lifetime.md](0052-support-facing-and-shell-lifetime.md) — サポート待機方向の変数更新、薬莢の着地ハンドラと範囲外破棄
- [0053-boss-support-and-cpu-input.md](0053-boss-support-and-cpu-input.md) — ボスヒルダの固定サポートを共通化対象から除外、CPUのD入力を既存COMへ接続
- [0054-vs-presentation-preload.md](0054-vs-presentation-preload.md) — ステージを先読みし、顔グラ・BGM付きVS演出の裏でキャラとサポートをロード。VS／ストーリー共通経路、常駐portrait、暗転での戦闘画面公開
- [0055-loading-main-thread-budget.md](0055-loading-main-thread-budget.md) — 素材列挙のコルーチン分割と型付きTaskによる再帰型検査の撤去、停止時間の実測
- [0056-vs-loading-animation-wait.md](0056-vs-loading-animation-wait.md) — VSでの約3秒の静止は演出時計の停止。顔グラの待機ループと退出直前のロード待ちに変更
- [0057-escape-and-debug-title.md](0057-escape-and-debug-title.md) — 勝利デモ・ロード中のESC無効化と、全画面共通の開発用F8タイトル復帰
- [0058-player-update-0117-audit.md](0058-player-update-0117-audit.md) — 1月17日修正.playerの全10キャラ比較：素材同一、209技とあやね設定、シエラ個別消費量の共通化への影響

- [0059-support-owner-variant-audit.md](0059-support-owner-variant-audit.md) — 最新原作のサポートをゆいと比較：キャラ別の消費・威力・判定・分岐差と正規化比較ツール

- [0060-owner-support-packages.md](0060-owner-support-packages.md) — 1月17日.player更新と、サポート50ファイルへの使用キャラ別完全定義の分離・選択先読み
- [0061-saki-hilda-freeze-audit.md](0061-saki-hilda-freeze-audit.md) — サキ＋ヒルダの原作停止報告と、現行ランタイムの登場・待機・5種類の入力確認
- [0062-recoverable-combo-colour.md](0062-recoverable-combo-colour.md) — 受け身可能な追撃のV128をヒット時点で保持し、赤いコンボ文字・数字へ反映
- [0063-attract-memory-lifetime.md](0063-attract-memory-lifetime.md) — デモ／通常対戦終了時の技キャッシュ・対戦参照の解放、GCとプロセスメモリ測定
- [0064-memory-heap-audit.md](0064-memory-heap-audit.md) — GC後の生存量とOS確保領域の区別、L^弱参照表の削除反復による拡大と修正
- [0065-core-member-allocation-measurement.md](0065-core-member-allocation-measurement.md) — コアのメンバー名検索最適化後のGC回収数・メモリ使用量・update時間の再測定
- [0066-original-palette-rendering.md](0066-original-palette-rendering.md) — 原作EXEの8bit画像入力・16bitパレット参照・画面バッファ描画の確認
- [0067-process-memory-breakdown.md](0067-process-memory-breakdown.md) — 約1GBのOS領域別内訳、GCで消える約256MBと描画側の遅延解放約235MB
- [0068-render-audio-resource-reuse-audit.md](0068-render-audio-resource-reuse-audit.md) — 画像・Shaderの再利用、描画ごとのQuad生成と共通音声Sourceの再生ごとの複製
- [0069-writecombine-allocation-trace.md](0069-writecombine-allocation-trace.md) — WriteCombine約446MBの確保スタック追跡、Vulkan画像プールと描画基盤の内訳、試合中GCの確認
- [0070-battle-growth-gc-backlog.md](0070-battle-growth-gc-backlog.md) — 通常速度の試合中ヒープ増加、試合を維持したフルGC前後、回収されたテーブル・コルーチン等の直接計数
- [0071-gc-pacing-tuning.md](0071-gc-pacing-tuning.md) — 新GC APIでgrowth=120/stepmul=800/stepsize=10を採用、同一CPU戦のメモリ・処理時間比較
- [0072-sweep-down-residual-hurtboxes.md](0072-sweep-down-residual-hurtboxes.md) — ゆい・サキ・えり2Cのダウン再ヒット、被弾前のFD持ち越しと診断比較
- [0073-corner-recoil-audit.md](0073-corner-recoil-audit.md) — 原作EXEの画面端超過量の返却、壁DS、ゆい6B→えりの過剰後退を生む空中境界の訂正と回帰テスト
- [0074-fm2k-vm-coverage-audit.md](0074-fm2k-vm-coverage-audit.md) — VM命令・イベント・入力・衝突の横断監査、未対応箇所の自動抽出、COMとダウンFD持ち越しの診断

- [0075-ds-transition-com-history.md](0075-ds-transition-com-history.md) — P0実装：DS専用初期化、技内COMの履歴窓と非消費照合、実データ回帰テスト

- [0076-variable-semantics.md](0076-variable-semantics.md) — P2実装：Vの符号付き16ビット代入・加算飽和・座標整数化・オブジェクト単位の変数寿命

- [0077-afterimages-and-rp-depth.md](0077-afterimages-and-rp-depth.md) — AI残像履歴・色補間、RP優先度、RC/EBの原作でも無効な指定の確認
- [0078-ps-additive-hitstop.md](0078-ps-additive-hitstop.md) — PSの加算式停止時間、0指定による停止解除の誤り、ゆい6B→214Bの画面端コンボ復旧
- [0079-command-buffering.md](0079-command-buffering.md) — コマンド表の履歴窓による先行入力、硬直終了直後の受付、ヒットストップ中の受け身判定凍結と通常色コンボ検証
- [0080-fa-contact-offset-event.md](0080-fa-contact-offset-event.md) — FA同士の接触からoffsetWayを発火、影を利用したえり214Aの裏回り・ソバット分岐
- [0081-throw-and-hit-events.md](0081-throw-and-hit-events.md) — whileThrowDo、FDのthrow属性、本体の命中イベント確定・相打ち抑制・DS優先順位
- [0082-event-remaining-audit.md](0082-event-remaining-audit.md) — 全イベントに発火元があることと完全再現の区別、着地専用遷移・生成物命中・相殺時defending・処理順の残件
- [0083-remaining-event-paths.md](0083-remaining-event-paths.md) — 残る4イベント経路、原作の戦闘更新順、被弾反応の予約と相打ち、FA属性ビットの補完
- [0084-db-object-chip.md](0084-db-object-chip.md) — UnknownだったDBの復元、Oの存在時分岐・削除・depth、FAガード削り、VM対応の残件
- [0085-command-range-repeat-charge.md](0085-command-range-repeat-charge.md) — キャラ別間合いによる近遠技の選択、連打・溜め入力と保持履歴
- [0086-command-scan-performance.md](0086-command-scan-performance.md) — 36FPS低下の再現、旧コミット比較、入力履歴の不成立判定で安定区間75FPSへ改善

- [0087-decoration-collision-performance.md](0087-decoration-collision-performance.md) — 演出オブジェクト増加時の接触・被弾判定負荷削減と計測。

- [0088-life-and-cancel-rules.md](0088-life-and-cancel-rules.md) — 通常命中・削り・GPの低体力補正、FA確認とCの移行先制限、VP未使用機能の対象外化。

- [0089-combo-damage-correction.md](0089-combo-damage-correction.md) — キャラ別コンボ補正、FD・低体力補正の順序、被弾側ヒットカウンタの寿命。

- [0090-command-button-edges.md](0090-command-button-edges.md) — 通常コマンド・COMの保持履歴からの押下判定。

- [0091-command-history-consumption.md](0091-command-history-consumption.md) — コマンド成立時の古い履歴消費と20フレーム境界。

- [0092-command-rotation-order.md](0092-command-rotation-order.md) — 回転入力の順序と斜め入力の扱い。

- [0093-input-facing-audit.md](0093-input-facing-audit.md) — VPは記録時に相対方向化。向き変更の実装変更不要を確認。

- [0094-script-return-slots.md](0094-script-return-slots.md) — SC/SFの固定復帰先とE・SG・DSの相互作用。

- [0095-motion-fixed-point.md](0095-motion-fixed-point.md) — Mの整数係数・符号・保持と32bit加算境界。

- [0096-random-gauge-boundaries.md](0096-random-gauge-boundaries.md) — Rndの端点、GL/GS/GPの比較・消費・数値境界。

- [0097-unused-gauge-fallback.md](0097-unused-gauge-fallback.md) — GL/GS分岐先0は現行VPで未使用、対象外へ整理。

- [0098-color-and-sound-settings-inventory.md](0098-color-and-sound-settings-inventory.md) — COLORの透明度指定・使用範囲と音声メタデータの棚卸し。

- [0099-sound-stop-semantics.md](0099-sound-stop-semantics.md) — Sの音源種別0による全音声停止と通常再生の照合。

- [0100-layer-scroll-rounding.md](0100-layer-scroll-rounding.md) — レイヤーの整数スクロール、使用中のループ指定と実ステージ描画検証。

- [0101-blend-audit-completion.md](0101-blend-audit-completion.md) — 5合成方式のGPU画素検証、了承済み描画差と0074の対象範囲完了。

- [0102-hit-reaction-facing.md](0102-hit-reaction-facing.md) — 命中位置ではなく攻撃オブジェクトの向きに基づくヒット・ガード反応。

- [0103-sierra-startup-routing.md](0103-sierra-startup-routing.md) — シエラの初期化を選択パッケージへ接続、単独ロードでの全入力回帰。

- [0104-ignore-direction-offset.md](0104-ignore-direction-offset.md) — 向き無視のI命令を画像位置と残像にも適用。

- [0105-turn-and-ko-completion.md](0105-turn-and-ko-completion.md) — 着地硬直後の先行入力前の振り向き、KO後の演出保護と技終了待ち。

- [0106-distribution-engine-check.md](0106-distribution-engine-check.md) — 配布ビルド前にコンパイラとVMの互換性を実行検証。

- [0107-air-attack-landing-facing.md](0107-air-attack-landing-facing.md) — 空中C後の着地硬直中の振り向きと、着地未処理時の地上技開始防止。

- [0108-compile-parallelism.md](0108-compile-parallelism.md) — VM-only向けLTONコンパイルの直列処理・共有ロック調査と1/6並列の実測。

- [0109-sierra-aim-direction.md](0109-sierra-aim-direction.md) — シエラ6Dの照準方向を射撃終了まで維持する生成時パッチ。

- [0110-direct-asset-packaging.md](0110-direct-asset-packaging.md) — 素材の2回の中間コピーを廃止し、元ファイルから直接ZIPへ格納。

- [0111-natalia-official-name.md](0111-natalia-official-name.md) — 内部名カテジナを正式名ナタリアへ統一し、素材・生成データ・変換処理を更新。

- [0112-parallel-lton-packaging.md](0112-parallel-lton-packaging.md) — 物理コア数に応じたLTON並列コンパイルと直列生成物との比較。

- [0113-natalia-throw-reaction-input.md](0113-natalia-throw-reaction-input.md) — ナタリア投げのレベル0やられ動作へのコマンド割り込みを原作の被弾状態制限で防止。

- [0114-select-confirmed-palette.md](0114-select-confirmed-palette.md) — キャラ決定時に顔グラ本体と既存の子オブジェクトへ確定パレットを即時反映。

- [0115-native-lton-threads.md](0115-native-lton-threads.md) — lovec内のLTONマルチスレッド化と、ゲーム側の複数プロセス処理の廃止。

- [0116-vs-return-selection.md](0116-vs-return-selection.md) — VS対戦後のキャラセレで両者の直前の使用キャラにカーソルを合わせる。

- [0117-vs-return-support.md](0117-vs-return-support.md) — VS対戦後に両者のサポート選択も復元。隠しヒルダのみえこへ戻す。

- [0118-eko-media-ownership-and-variants.md](0118-eko-media-ownership-and-variants.md) — ゆい・はるか固有画像とえこ151枚の整理、パレット差による重複候補の監査。

- [0119-kanae-media-ownership.md](0119-kanae-media-ownership.md) — かなえ専用PNG12枚を分類し、他キャラ・サポートからの132参照を維持。
