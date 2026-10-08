# 配布時の素材中間コピーを廃止

2026-10-08。0108の調査を受け、画像・音声等を元ファイルから直接ZIPへ格納する方式へ変更した。

後続の [0112-parallel-lton-packaging.md](0112-parallel-lton-packaging.md) でLTONの並列コンパイルも追加した。以下は素材コピー廃止時点の記録。

## 処理

`tools/dist.ps1` は従来どおりエンジンの互換性を確認してから `tools/package-game.ps1` を呼ぶ。

1. `main.lh`、`conf.lton` と `src`・`assets`・`data` 配下を列挙する。従来どおり `skills`・`_conversion` ディレクトリと `data.lton`・`support-source.lton` を除外する。
2. `.lh`・`.lton` だけを `build/package/source` へコピーし、`--compile-game` で `build/package/compiled` へコンパイルする。
3. ZIP内の `.lh`・`.lton` はコンパイル結果から、それ以外はプロジェクト内の元ファイルから直接格納する。空ディレクトリも維持する。
4. 完成したZIPで `build/VanguardPrincess.love` を置換し、配布用VMと結合して `dist/VanguardPrincess/VanguardPrincess.exe` を作る。

画像・音声の `元→stage→game` という2回のコピーがなくなる。エンジン本体の変更は不要。LTONコンパイルの並列化は今回の変更には含めない。VS Codeの既存の配布タスクもそのまま使える。

コンパイルまたはZIP作成が失敗した場合、既存の `.love` と配布ディレクトリは置換しない。ZIPは一時ファイルで構築し、成功時だけ置換する。作業ディレクトリの清掃は対象の絶対パス・親ディレクトリを検査してから行う。古い `build/stage`・`build/game` は今回の処理では参照・削除しない。

## 検証

`python tools/test-package.py`:

- 旧方式でコピー・コンパイルしたファイルと、新ZIP内の全ファイルがバイト単位で一致。
- 除外ディレクトリ・ファイル、未参照LH、空ディレクトリ、日本語・空白・角括弧を含むパスを検証。
- 中間フォルダに `.lh`・`.lton` 以外がないことを検証。
- VM-onlyでZIPを実行し、素材読込・コンパイル済みLTON読込・require先の関数呼出の結果を終了コード17で確認。
- 古い作業フォルダの再利用拒否、コンパイル失敗時の既存ZIP維持、元ファイルの不変を検証。

実ゲームの `tools/dist.ps1` も完走。最終版の測定は素材を含むZIP・EXE作成まで42.67秒（コード・データの準備2.04秒、コンパイル16.18秒、ZIP18.34秒、残りは互換性確認・列挙・清掃・EXE作成等）。直前の試行は52.91秒であり、キャッシュと他の負荷による変動がある。0108の旧方式120.72秒は `--compile-game` 単体の値なので、同条件の配布全体の速度比としては扱わない。

出力は8,822ファイルと1空ディレクトリ、配布EXEは約252.4 MiB。実ゲームの全操作の回帰試験を行ったという意味ではない。

実ゲームの最終ZIPについても、214個のコンパイル済みファイルと8,608個の元素材を全件SHA-256で照合し一致した。以前の `build/parallel-baseline` とファイル名集合も一致し、配布EXEの先頭がshipping VM、その後が検証済みZIPと完全一致することを確認した（検証スクリプト: `build/verify-direct-package.py`）。
