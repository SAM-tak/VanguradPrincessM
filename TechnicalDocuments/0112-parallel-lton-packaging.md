# 配布時のLTON並列コンパイル

2026-10-08。`tools/package-game.ps1` と `tools/dist.ps1` に `-Jobs` を追加した。

以下は旧・複数プロセス方式の記録。現在の実装は [0115-native-lton-threads.md](0115-native-lton-threads.md) のlovec内マルチスレッド方式へ置き換え済み。`-Jobs` の操作は同じ。

- 既定値0は `Win32_Processor.NumberOfCores` の合計（物理コア数）を使用する。このPCでは6。検出できない場合は警告して1へフォールバックする。
- `-Jobs 1` は従来の直列コンパイル。指定値は0〜256、実際のワーカー数はLTONファイル数を上限とする。
- `.lh` は従来どおり同じプログラムでまとめて検査・コンパイルする。依存関係の並列処理はしない。
- LTONは大きい順に累積バイト数が最も小さいワーカーへ割り当てる。独立したlovecプロセスなので、Runtimeのプロセス共通ロックを競合しない。
- ワーカー入力には元の相対パスを維持したLTONと最小のmain.lhを置く。全ワーカー成功後、割り当てたLTONの出力だけを `build/package/compiled` へ集める。合成したmain.lhは配布に含めない。
- ワーカーのstdout/stderrは非同期に読み出し、`build/package/lton/<番号>/*.log` に保存する。失敗時は未終了の子プロセスを停止し、ZIP作成へ進まない。既存の配布物は保持する。
- 0110で導入した画像・音声の直接ZIP格納は継続する。

```powershell
pwsh -NoProfile -File tools/dist.ps1           # 物理コア数（このPCでは6）
pwsh -NoProfile -File tools/dist.ps1 -Jobs 3   # 最大3並列
pwsh -NoProfile -File tools/dist.ps1 -Jobs 1   # 直列
```

VS Codeの既存配布タスクも、変更なしで既定の並列化を利用する。

検証: `python tools/test-package.py` が成功。直列・並列・従来の全ファイルコピー方式の生成物を比較し、全内容が一致した。未参照LH、異なるフォルダの同名LTON、日本語・空白を含むパス、除外設定、空ディレクトリを含む。VM-onlyで直列版・並列版ZIPを実行し、素材・LTON・require先の動作を確認した。不正なLTONによるワーカー失敗時も既存ZIPが維持された。

実ゲームでも既定の6ワーカー、LH 18ファイル・LTON 196ファイルで配布ビルドが完走した。準備1.77秒、コンパイル工程全体6.42秒（LH処理・LTONワーカー起動・出力集約を含む）、ZIP15.95秒、配布EXE作成まで30.93秒。ワーカーの入力スナップショットを再構成して直列コンパイルすると12.79秒で、214個すべての生成物のSHA-256が並列版と一致した。単発測定であり、キャッシュや他の負荷の影響は残る。

直列比較の記録: `build/parallel-verify-cad52b0ad0134b19a97c368cc973c3a4`。小規模テストでVM実行を確認したが、実ゲーム全操作の回帰試験ではない。
