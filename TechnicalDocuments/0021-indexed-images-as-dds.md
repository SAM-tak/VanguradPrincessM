# 0021: パレット画像を DDS（R8）で持つ

- **日付**: 2026-10-04
- **状態**: 適用済み。全素材を変換し直し、参照 25,052 件が実在。試合の表示（色・サポート・HUD・コンボ表示）を確認

## 理由

- 読み込んだテクスチャは解放されず（キャッシュが持ち続ける）、全部読むと RGBA で約 1.8GB（images.lton の幅×高さから試算）
- パレット画像（大半）は 1 画素 = パレット番号 1 バイトで足りる。PNG も 8bit グレースケールで 1 チャンネルを格納できる（今までそうしていた）が、
  **LÖVE の PNG デコーダ（lodepng）は常に RGBA8 に展開する**（実測: グレースケール PNG → `rgba8`）。TGA も stb_image で RGBA8
- **DDS は非圧縮 R8 を扱える**（lhat-love の ddsparse）。今の `love.graphics.newImage(path)` のまま **`r8` テクスチャ**になる（実測）。エンジンの変更は不要
  - **ヘッダは古い L8 形式**（DDPF_LUMINANCE、8 ビット、R マスク 0xFF）。ddsparse はこれを R8_UNORM として読む
  - 最初は DX10 拡張ヘッダ（DXGI_FORMAT_R8_UNORM = 61）で書いたが、LÖVE では読めても IrfanView・Pillow が読めない
    （Pillow: "Unimplemented DXGI format 61"。ユーザー指摘）→ L8 に変えた（2026-10-04）。既存の 4,444 ファイルはヘッダだけ書き換え（画素は同じ）
  - DDS は入れ物で、LÖVE はどの環境でも読める。環境依存なのは中の GPU 圧縮形式（BC 系はモバイル非対応）で、非圧縮 R8 は関係ない
  - パレットのシェーダは元から R チャンネル（`c.r`）だけを見る
- 代わりにディスク上は大きい（非圧縮）: 例 8KB の PNG → 69KB。assets 全体 404MB → 584MB（共有分 19 → 39MB）。
  fused の .love は zip（deflate）なので配布物はある程度縮む（未計測）

## 変換

- `convert.py`: パレット画像は `images/NNNN.dds`（`write_dds_r8`: "DDS " + 124 バイトの L8 ヘッダ + 幅×高さの画素）、
  自前のパレットを持つ画像は従来どおり `images/NNNN.png`（RGBA）。images.lton の `file` も拡張子込み
- `share_assets.py`: 同じ素材かは**中身の鍵**（`content_key`）で見る。音はバイト列、画像は「大きさ・モード・画素」の SHA-1
  → 同じ絵なら PNG でも DDS でも同じ鍵。共有プールのファイル名は `<鍵>.dds|png|wav`
  - `share_owners.txt` も同じ鍵（先頭 12 桁）に付け替えた（以前は PNG ファイルの SHA-1）
- `preview_gif.py`: images.lton の項目からファイルを決め、DDS も読む

## 手順（変換し直すとき）

1. `convert.py <json dir> <out> -j 6`（約 3 分）
2. `gen_script.py` の script.lton、`read_demos.py` の demos.lton、フォントを用意（convert.py は作らない）
3. `share_assets.py <out> --apply`（約 1 分）

今回は新しい木を `build/` に作り、参照を確かめてから assets に反映した（エディタが assets のファイルを開いているとフォルダごとの移動はできない）。

## 未対応

- テクスチャの解放（場面ごとにまとめて捨てる仕組み）。LÖVE にリソースアリーナは無い。`Object:release()` は lhat-love に未バインド
