# WriteCombine領域の確保元追跡

2026-10-06。b663075後、同日14:02:53のlhat-loveビルドで測定。ゲーム・L^コア・lhat-loveの実装は変更していない。

## 結論

以前「描画側と考えられる」としていた約449MBは、今回の起動から試合開始までの追跡で **445,906,944 bytes**。GPU画像、描画バッファ、描画基盤の確保に対応した。L^のGCヒープや音声Sourceの領域ではない。

実際のレンダラーは `Vulkan 1.4.325 / Nvidia / NVIDIA GeForce GTX 1660 Ti`。OpenGLの実装だけを読んでも、この環境の確保元の説明にはならない。

| 確保経路 | bytes | 約MB（10進） |
| --- | ---: | ---: |
| VMA画像用割り当て | 379,584,512 | 379.6 |
| VMAバッファ用割り当て | 33,636,352 | 33.6 |
| descriptor set確保 | 2,015,232 | 2.0 |
| Vulkanインスタンス・デバイス初期化 | 10,878,976 | 10.9 |
| swapchain作成 | 18,944,000 | 18.9 |
| D3D/DXGI/ドライバー経路 | 847,872 | 0.8 |
| 合計 | 445,906,944 | 445.9 |

これは確保を発生させた経路別の分類であり、プール内の各画像の占有サイズまで分解したものではない。初期化スタックにgraphics-hook64.dllも存在するが、その存在だけから録画機能等が確保した量とは判定しない。

## 画像が大部分を占める根拠

ゲーム画像のnewImageから次の経路を直接確認した。

```
lh_newImage
  Graphics::vulkan::newTexture
  Texture::vulkan::loadVolatile
  vmaCreateImage
  VmaAllocator_T::AllocateMemory
  VmaBlockVector::CreateBlock
  NVIDIA vkAllocateMemory
  NtGdiDdDDICreateAllocation
```

この呼び出しの前後でPAGE_WRITECOMBINE領域が増加する。ゲーム画像に対応した確保は32、64、128、128MiBの4回、合計 **352MiB = 369,098,752 bytes**。Windows側では11個の32MiB領域となる。上表の画像用との差10MiBは描画初期化側の画像確保。

別の、ドライバー初期化後から追跡する実行ではvkAllocateMemoryの引数も採取した。上記4回のmemoryTypeIndexはすべて1。実機のVulkanメモリ情報を照会すると、type 1は約6GBのGPUメモリheap 0、propertyFlagsはDEVICE_LOCALのみ（HOST_VISIBLEではない）。単純に「CPU側に画像のコピーがさらに369MB残っている」と解釈するのは誤り。

同時点のLÖVE統計は画像1903個、texturememory **249,143,059 bytes**。LÖVE Vulkan実装はVulkan Memory Allocator（VMA）を使用し、Graphics.cpp:2023付近でpreferredLargeHeapBlockSizeを128MiBに設定している。大きな領域から各画像へ割り当てるため、論理的な画像サイズとOS/ドライバーの確保サイズは一致しない。差には配置・アラインメント・空き容量等が含まれる。差の全量を空き容量だとは断定していない。

画像転送用staging bufferはTexture.cppのuploadByteDataで別に作られ、queueCleanUp経由で破棄される。大部分の369MBはこの一時転送バッファではなくvmaCreateImage経路に対応する。

## GCは試合中も動作する

LHATOVE_GC_STATSを有効にした同じ実行で、試合開始からVSテスト完了までのcollectedは **86,838 → 3,221,300**。タイトルに戻る前にも約313万個を回収しており、「試合中はGCが一度も動かず、タイトルで初めて回収される」という挙動ではない。

テストは1描画あたり複数回updateして実際の試合を進めるため、通常速度のメモリ推移・ピークを再現するベンチマークではない。ユーザーの320→760MBの増加全量をこのログだけで分類したわけではない。GC稼働中でも回収待ち・生存データ・ヒープの確保余裕によってメモリが増える可能性は残る。

WriteCombineはメモリのキャッシュ属性であり、RAM常駐量を示す名称ではない。今回の試合開始スナップショットはprivate約902MB、working set約471MB。以前の0067でもWriteCombineの大部分は非常駐だった。これらにGPU画像の論理サイズを加算して消費RAMとすることはできない。

## 測定方法と限界

自分で起動したlovec.exeを開始前に停止し、診断DLLでNtGdiDdDDICreateAllocation等を追跡。各呼び出し前後のVirtualQuery結果から新たなWriteCombineアドレス範囲を採取し、試合開始時の残存領域と照合した。隣接領域が結合される場合も、前後の区間差分だけを計上。重なる履歴は新しい確保を優先。今回の残存領域はすべていずれかの確保履歴に対応した。

LÖVEリリースDLLにはデバッグ情報がなかったため、既存オブジェクトを診断用の別出力先へ再リンクしてmapを取得。実行DLLと診断DLLの.textのRVA、サイズ、SHA256が一致することを確認した（SHA256: 1fbda0525ac4c1e09eec4413e04c19011636facd2278e462413f5803160de79f）。古いPDBやexport名からの遠いオフセットを関数の根拠にしていない。NVIDIA内部の詳細な用途までは公開シンボルがなく未分類。

診断DLLの固定ログ領域等による計測自体のメモリ負荷がある。各GDI確保の前後にはプロセス全体の領域を比較するので、別スレッドから同時確保される場合の厳密な帰属には限界がある。画像部分は別実行のvkAllocateMemory引数・スタック・増加量でも照合した。

生ログ・診断コードは無視対象のbuild/wc-*、build/classify-wc.py、build/linkprobe/に保存。フックは自分で起動した計測プロセス内だけで、終了後には残らない。配布用実装へのフック・GC強制・メモリ設定変更は行っていない。
