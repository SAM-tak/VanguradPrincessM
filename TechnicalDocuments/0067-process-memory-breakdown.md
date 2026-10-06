# 0067: 約1GBのプロセスメモリの内訳

2026-10-06。画像形式を変更せず、現在の約1GBの使用量の所在を調査した。

## 方法

- 対象: 2026-10-06 14:02:53ビルドの `love.dll`（10,185,728 bytes）。コア／LÔVEのソース変更・再ビルドは行っていない。
- `build/gc-audit.lh` を元に、ゆい同士のVS戦（seed 42）、2ラウンド決着、ESCでタイトル復帰を実行。
- スナップショット前に明示的GCを行い、各時点で12秒間シミュレーション更新を止めて描画を継続する計測用エントリーを生成。通常ゲームの仕様は変更していない。
- GetProcessMemoryInfoでprivate bytesとworking setを取得。VirtualQueryExでコミット済み領域と保護属性を記録。
- Microsoft Sysinternals VMMapのCSVでヒープ、画像モジュール、その他private dataを分類。CSVの数値はKiB、以下は換算して十進MB。
- 一時的な独立DLL `build/heap-snapshot.dll` を、自分で起動したテストプロセスにのみロード。GetProcessHeaps / HeapLock / HeapWalkで使用中ブロック量を採取。ゲームやコアのソースは書き換えていない。DLLはプロセス終了で消える。
- private bytesが1.15GBを超えた時点のヒープと領域を外部から記録し、その後テストエントリーへファイルで合図して `L^.collectgarbage()` だけ行う比較も実施。
- 全体ETWでの確保元スタック取得は管理者権限不足で使えなかった。既存のETWセッションの停止・設定変更はしていない。したがって、全領域の確保元関数まで特定した結果ではない。

計測ツール: `build/capture-memory-map.py`, `build/remote-memory-audit.py`, `build/heap-snapshot.c`。出力: `build/map-forced-gc-run.log`, `build/map-*.csv`, `build/heap-*.csv`, `build/regions-*.json`, `build/memory-map-samples.json`, `build/memory-breakdown-summary.json`。これらはローカル調査用でbuild配下、配布物に含めない。終了時に一時エントリーと合図ファイルは削除。

## 約1.15GBの内訳

| 分類 | 試合中の高使用量時 | タイトル復帰後・落ち着いた時点 |
|---|---:|---:|
| 通常ヒープのコミット領域（空き・管理領域も含む） | 約583MB | 約247MB |
| PAGE_WRITECOMBINE領域 | 約449MB | 約181MB |
| それ以外のヒープ外private data | 約77MB | 約77MB |
| DLL／EXEのprivate領域 | 約38MB | 約38MB |
| スレッドスタック | 約1MB | 約1MB |
| VM領域からの合計 | 約1,148MB | 約544MB |

高使用量時の領域はVirtualQueryExで採り、同一プロセスの前後のVMMap allocation範囲に対応づけた。Heap (Private Data) 583,442,432 bytes、WriteCombine 449,052,672 bytes、その他private data 76,726,272 bytes、stack 1,167,360 bytes。採取中もプロセスが進むこと、集計方法が異なることから、GetProcessMemoryInfoの約1,151MB／547MBとは数MBの差がある。

DLLのprivate領域のうち、VMMapで `nvwgf2umx.dll` が27,124KiB、`nvoglv64.dll` が2,212KiB。この合計約30MBはNVIDIAの描画ドライバーのモジュール領域と特定できる。

## 一時データが約256MBを占めた

高使用量時のHeapWalk使用中ブロックは **510,097,552 bytes**。試合を終了させずGCだけ行った後は **254,000,494 bytes**。約256MB減った。

その間、テクスチャは **1,903枚／249,143,059 bytes**、WriteCombineは **449,052,672 bytes**のまま。private bytesは約1,151MBから約888MB、working setは約711MBから約456MBへ減少した。キャラやステージ素材の破棄による減少ではない。

GC後のヒープ計測まで約3秒描画を続けるため、差分は瞬間的な完全同期値ではないが、回収待ち一時データが数百MBあるという結論は変わらない。高使用量時のHeapWalkブロック数は約244万、GC後約110万。これはL^オブジェクト数ではなく、内部配列などを含むネイティブヒープブロック数。

現行コア `gc.c` は回収完了後の閾値を `objects.count * LHAT_GC_GROWTH_FACTOR + LHAT_GC_MIN_THRESHOLD` とし、config.hの成長係数は2。処理中は固定個数単位で進む。オブジェクト数基準であり、ここで測った数百MBを直接上限管理するものではない。数の削減だけでピークメモリが同じ比率で下がらないこととも整合する。

## タイトル復帰時の約235MBは数秒遅れて消える

最終測定の同じタイトルで:

| 時点 | Private bytes | Working set | WriteCombine |
|---|---:|---:|---:|
| タイトル復帰後・計測開始 | 782.4MB | 378.8MB | 415.5MB |
| 1秒後 | 782.4MB | 378.8MB | 415.5MB |
| 計3秒後 | 547.1MB | 378.8MB | 180.6MB |

WriteCombineの減少は **234,881,024 bytes = 7 × 32MiB**。この確認ではVMMapを呼ぶ**前**にVirtualQueryExとGetProcessMemoryInfoだけで減少を観測した。VMMapが解放を引き起こしたわけではない。

テクスチャは356枚／56,973,269 bytesのまま、working setも変わらない。描画リソース破棄に伴うドライバー側の遅延解放と整合する。PAGE_WRITECOMBINE自体はデバイス用属性であり、属性だけから全ブロックを特定のOpenGL関数／テクスチャに帰属させることはできない。

0065のタイトル時約820MBは、復帰後30〜90フレーム周辺の短時間観測だった。これを「長く待っても残る量」と解釈するのは不適切。今回、数秒後の約550MBを別に確認した。

## 残る約550MB

通常ヒープ約247MBのうち使用中ブロックは **181,223,066 bytes**。差の約66MBには空き領域と管理領域がある。残りはWriteCombine約181MB、ヒープ外private約77MB、モジュールprivate約38MB等。

0064の別ビルドでのコア全割り当て計測は約95MBだったが、それを今回の181MBに含まれる正確なL^使用量として転用はしない。ヒープの使用中181MBについて、L^定義データ／音声／描画ライブラリ等への全件分類は未実施。ヒープ外約77MBの確保元も未特定。これらは今回の調査の限界。

テクスチャ統計約57MBはGPUリソースの論理サイズであり、上表に別項目として足してはいけない。プロセスのCPU仮想メモリとGPU割り当て／マッピングは異なる指標で、重複計上となりうる。

今回の試合中最大観測はprivate約1.21GB／working set約762MB。計測停止と明示的GCを含むため、通常プレイの厳密なピーク比較ではない。約1GBがすべてRAM常駐量という意味でも、すべて生存ゲームデータという意味でもない。

## 次の調査・改善候補

大きい改善余地として実測できたのは、画像形式ではなく回収待ち一時データの数百MB。対策を検討するならコアのGC開始条件・進行量・バイト量ベースの管理が対象。毎フレームの強制フルGC等のゲーム側ワークアラウンドは入れていない。

さらに所有者別へ分解するには確保元スタック付きトレースが必要。今回の結果はOS領域分類とGC前後比較であり、全約550MBのオブジェクト単位の会計が完了したという意味ではない。

参考: [VMMap](https://learn.microsoft.com/en-us/sysinternals/downloads/vmmap)、[Memory Protection Constants](https://learn.microsoft.com/en-us/windows/win32/memory/memory-protection-constants)、[Working Set](https://learn.microsoft.com/en-us/windows/win32/memory/working-set)。
