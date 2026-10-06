# 0068: 描画・音声リソースの使い回し調査

2026-10-06。0067のWriteCombine約449MBについて、ゲームが使い捨てリソースを大量生成していないかを静的に確認した。実装変更は行っていない。

## 画像と描画

- `resource.lh` のロード完了処理でImageDataからTextureを作り、ImageDataはdisposeする。TextureはArenaに保持。
- `arena.texture` はArena内のパス別キャッシュを検索し、見つからない場合のみ同期生成してキャッシュする。Sheetも画像番号別にTexture参照を保持。
- `sprite.lh` のパレットShaderは1個だけ遅延生成して保持。描画ごとに作り直さない。
- デバッグFontも初回のみ生成して保持。
- ゲームコードにCanvas／Mesh／Textの毎フレーム生成はない。
- 各スプライトでShaderのuniform送信、Shader設定・解除、色・合成モード設定を行う。描画呼び出しだけではないが、これらはゲーム側でTextureを作り直す処理ではない。
- 例外として `Sheet.drawPart` は呼び出しごとに `newQuad` を行う。HUDのゲージ等で使用。再利用できるCPU側オブジェクトを毎回作っている。
- LÔVEの `graphics/Quad.h` / `Quad.cpp` を確認。Quadは頂点座標・UV・viewport等を持ち、TextureやGPUバッファを自身で確保しない。この生成を数百MBのWriteCombine領域へ直結させる根拠はない。

## 音声

- `Fighter.sound` は所有キャラの番号別Sourceキャッシュを使い、同じSourceをstop/playして再利用する。
- `Fighter.soundFrom` は毎回 `arena.sound` を呼ぶ。`arena.sound` は準備済みSourceのcloneを返し、Arena.sourcesへ追加する。したがって、共通定義経由の効果音には再生ごとのSource生成がある。
- ポーズ音等にも同様の直接呼び出しがある。
- Sourceは即破棄されるのではなく、Arena終了まで保持される。再生済みSourceを再利用するキャッシュやプールをゲーム側に設ける余地がある。同時再生と所有者ごとの再生状態には注意が必要。
- LÔVEの `audio/openal/Source.cpp` のコピーコンストラクタではstaticBufferを共有する。static音声のcloneごとに波形全体を複製する処理ではない。streamのcloneにはdecoderとバッファの作成があるため、すべてのSource複製を同じ費用とは扱わない。

## WriteCombineとの関係

0067では試合中のTexture論理サイズは約249MB、枚数1,903でGC前後に変わらず、WriteCombine約449MBも変わらなかった。現時点で「毎フレーム画像を作って捨てていることが449MBの原因」という証拠はない。

Quadの再利用と共通音声Sourceの再利用は改善対象として確認できたが、WriteCombineの確保元はまだスタック追跡で特定していない。ドライバー側の画像配置・転送・余剰領域などを、確定した内訳として扱わない。

## Quad再利用への変更

ユーザーの指示により、`Sheet.drawPart` のQuadをモジュール内の1個に変更した。初回のみ生成し、その後は6引数の `setViewport` で切り抜き範囲と画像全体の幅・高さを更新する。画像寸法が異なる場合や左右反転も元の描画計算を維持する。

LÔVEの `graphics/Texture.cpp` のdraw処理は、その呼び出し中にQuadの頂点・UVを描画バッファへコピーするため、次のdrawで同じQuadを書き換えても前の描画内容には影響しない。QuadはTextureを保持しないので、Arenaの切り替えで破棄せず再利用できる。音声Sourceの扱いは今回変更していない。

## 続く指示による共通音声Sourceの再利用

`Fighter.soundFrom` に所有キャラのパス別Sourceキャッシュを追加した。初回だけArenaのテンプレートから独立した再生Sourceを取得し、以降は同じSourceをstop/playする。1P・2Pの再生状態を独立させるための初回cloneは維持し、再生ごとのcloneを撤去した。子オブジェクトは所有キャラのキャッシュを参照する。

番号別とパス別キャッシュの世代更新は `freshSounds` にまとめ、Arena破棄後は両方をクリアする。旧実装は通常音声では初回取得をキャッシュしていたが、共通定義経由ではそれが抜けており、Arena.soundの「呼び出すたびに独立Sourceを作る」動作が毎回発生していた。

検証: `vs-memory-return` が実際のHUD描画を含む対戦→タイトル復帰3周を通過。`sound-reuse` が200回の再生でSource数不変、子と親の共有、対戦相手との独立、シーン変更後の再取得、同期フォールバック0件を確認した。ログは `build/quad-reuse-vs.log` と `build/sound-reuse.log`。
