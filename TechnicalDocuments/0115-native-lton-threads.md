# lovec内でのLTONマルチスレッドコンパイル

2026-10-08。0112の複数プロセス方式を、lovec自身の複数スレッド方式へ置き換えた。

```powershell
lovec --compile-game out --jobs 6 game
pwsh -NoProfile -File tools/dist.ps1 -Jobs 6
```

`--jobs` は0〜256。既定0はWindowsの物理コア数を使い、このPCでは6スレッド。検出失敗時・Windows以外では1。ファイル数を超えるスレッドは起動しない。1は直列。`.lh` の依存グラフの検査・コンパイルと素材コピーは直列のまま。

## 実装

- lhat-love `src/lh/Boot.cpp`: LTON一覧をサイズ降順に並べ、共有キューからワーカーへ動的に割り当てる。各ワーカーは独立したRuntime・Loaderを持ち、program、型領域、診断、loaderのバイナリ判定キャッシュを共有しない。元の相対パスを保ち、PhysFS経由でディレクトリ・ZIP双方を扱う。
- 型登録はプロセス内の共有情報を書き換えるため、全ワーカーの生成・登録をメインスレッドで終えてから実行する。失敗時は新規タスクの取得を停止し、既存スレッドの終了を待ってから診断を返す。スレッド生成途中の例外でもjoinしてからRuntimeを破棄する。
- lhat-love `src/lh/lh.cpp`・`lh.h`: program書込ロックをプロセス共通からRuntimeごとのmutexへ変更。同じprogramを使う言語スレッドの排他は維持する。
- lhat `src/program.c`: `lhat_program_new` で共有CastFailureを先に初期化する。これにより並列check/serialize時の遅延初期化競合を避ける。APIヘッダにもprogram生成・登録を先に直列で済ませる契約を記載。
- `tools/package-game.ps1`: 複数プロセスの分配・起動・ログ・出力集約を削除し、従来どおりスクリプト類だけをstageへ入れ、`--jobs` を付けてlovecを1回呼ぶ。素材を元の場所から直接ZIPへ入れる処理は維持。

エンジンだけでなく、上記lhatの変更も一緒にビルドする必要がある。バイナリ形式は変更していない。

## 検証

- 通常版・VM-only shipping版を再ビルド。
- `testing/test_parallel_lton.py`: 25個のLTONを6スレッドで繰り返し処理。直列版とのバイト一致、デバッグ名あり・なし、ディレクトリ・ZIP入力、CastFailureを使う式、VMでの実行、空・単一キュー、引数エラー、構文エラー、出力書込失敗を確認。
- 既存CLIテスト34件が成功。
- lhatのprogram・serialize・lton・thread・channel・taskの6テストターゲットを再ビルドし、全件成功。
- `python tools/test-package.py` で配布ZIPの直列・並列一致、VM実行、失敗時の既存ZIP維持を確認。
- 実ゲーム196 LTON・18 LHで、既定6スレッドの配布ビルドが完走。準備1.75秒、コンパイル6.86秒、ZIP19.30秒、配布EXE作成まで33.17秒。単発測定であり、以前の複数プロセス方式より速いと主張する比較ではない。
- 同じ `build/package/source` を `--jobs 1` で処理すると11.51秒で、214ファイルすべてのSHA-256がスレッド版と一致した。直列出力: `build/native-serial-31b5b535ed9d4b2eb59f673d3c0eddde`。
