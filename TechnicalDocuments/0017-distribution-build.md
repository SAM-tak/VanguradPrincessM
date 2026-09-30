# 0017: 配布ビルド（VM のみ・fused）

- **日付**: 2026-09-30
- **状態**: `tools/dist.ps1`（VS Code のビルドタスク）で `dist/VanguardPrincess/` に配布物ができ、起動する

## 手順（`tools/dist.ps1`）

1. VM のみの配布用エンジン（lhat-love の `build-vmonly-shipping`）が、フル版の lovec より古ければ建て直す（`-RebuildEngine` で強制）
2. ゲームが読むもの（`main.lh`・`conf.lton`・`src`・`assets`）だけを `build/stage` に集める。`tools/`・ドナー・メモは入れない。
   assets のうち変換の中間データ（`skills/*.lton`・`data.lton`、計 100MB 近く）も外す。ゲームが読む `.lton` は script・images・sounds・demos だけ
3. フル版の `lovec --compile-game` で `build/game` に（ユニットはバイト列、他はそのまま複製）。`.lton` もバイナリになる（下記）
4. zip して `.love`、VM 版の `love.exe` の後ろに連結 → `dist/VanguardPrincess/VanguardPrincess.exe`。隣に DLL（`love.dll`・`SDL3.dll`・`OpenAL32.dll`）

VS Code: 「Build distribution (VM-only, fused)」（既定のビルドタスク）、「Build and run distribution」。

- 大きさ: exe 359MB（約 25,000 ファイル）。全体で 9 分弱（2026-09-30）。内訳は未計測（`--compile-game` の LTON が重いと推測。`script.lton` は 1 キャラ数 MB）

## はまったところ

- **VM 版は、同じ lhat で作ったユニットしか読まない**。古い VM 版にフル版の新しいユニットを食わせると
  `this binary unit was not written by this build of the library, or has been damaged`
- **lhat が変わったら、lhat-love のエンジン側の生成物（`src/lh/Signatures.h`・`BootBinary.h`・`NogameBinary.h`）も作り直す**
  （`scripts/regen-generated.ps1` → `build.ps1 -VmOnly -Shipping`）。
  古いままだと VM 版が起動時に `the signature table this build carries does not fit its registrations`。
  fused exe では「lhatove」というタイトルのエラー画面になる
- **VM 版の `std.lton.load` はテキストの LTON を読めない**（構文解析器が無い）。`catch^nil^` で握りつぶしているので、
  データが全部 nil になり、何も走らない真っ黒な画面になった。
  当初 `--compile-game` がバイナリにするのは `conf.lton` だけで、一時は lhat の CLI（`lhat --compile`）で残り 283 件を変換していた。
  → lhat-love 側で、`--compile-game` が全部の `.lton` をコンパイルするよう修正（2026-09-30）。`lovec --compile -o DIR x.lton` も可
- 試験実行は `lovec --no-error-screen`。付けないとエラー画面が Escape を待って終わらない
