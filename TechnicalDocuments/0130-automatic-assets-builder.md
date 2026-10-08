# アーカイブ・原作フォルダからassetsを自動構築

## 利用者向け入口

`tools/fm2k_convert/build_assets.py SOURCE DESTINATION` を追加。SOURCE は原作の自己解凍exe、通常7z、または解凍済みフォルダ。Windowsでも手動解凍しなくてよい。フォルダ内の唯一の .kgt を探し、その隣の .player/.stage/.demo/.kgt から画像・音声を取り出す。

配布ビルドには `asset-builder/` と `ASSETS.md` を付属する。Pythonとrequirements.txtの依存だけで動作し、7-Zipコマンド、原作exeの実行、Wine、.NET製パーサーを必要としない。

```sh
python -m pip install -r asset-builder/requirements.txt
python asset-builder/build_assets.py vanpri108.exe assets
# 解凍済みフォルダも可
python asset-builder/build_assets.py /path/to/vanpri108 assets
```

## 定義再生成と分離する理由

ゲームの配布版は技・CPU・ストーリーなどの定義と独立サポートパレットを既に内蔵している。利用者の原作から定義を再生成すると更新版や移植側修正を巻き戻すおそれがあるため、今回の入口は assets のみを出力する。dataを読み書きしない。

`assets-recipe.json` に既存の整理済み素材の内容ハッシュと配置先を記録する。8,492ファイル、7,856種類の内容。画像は寸法・画素形式・画素のハッシュ、音声はバイト列のハッシュで照合する。素材本体はこのJSONには含まない。

原作の画像・音声がレシピの内容と一致したときだけ指定先に保存する。そのため、正式名への変更、共有化、明示所有者の変更、サポートの画像統合を利用者側で再推定する必要がない。色番号を正規化したえこの代表画像は原作中の既存画像を保持したものなので、同様に復元できる。専用パレットは配布版data内のものを使う。

開発者が素材を整理した場合はレシピを更新する。

```sh
python tools/fm2k_convert/build_assets.py assets tools/fm2k_convert/assets-recipe.json --write-recipe
```

## バイナリ読取り

`raw_media.py` は共通ヘッダ、技目録39バイト、技ブロック16バイトを読み飛ばし、画像ヘッダ・圧縮画像、8組のパレット、音声バイト列を読む。画像の0埋め・リテラル・連長・後方参照圧縮を展開し、既存convert.pyと同じDDS L8 / RGBA PNG・黒透過へ変換する。画像以降のキャラ別設定や命令は解釈しない。

レイアウトと圧縮の参照元は xem85/fm2ndparser の BaseParser.cs（commit 7266d65b9ca486a619b6b10836ee0cfed734fefb）。MITのライセンスを licenses/fm2ndparser.txt に同梱した。

## 完了条件

出力先が既存なら拒否する。一時領域に構築し、全出力の内容を保存後に再読して確認する。必要素材に不足があれば配置先の例を表示して失敗し、完成先へ移動しない。すべて一致した場合のみ出力ディレクトリを公開する。原作と既存assetsは上書きしない。

## 検証

- 未解凍の vanpri108.exe から全8,492ファイルを再構築し、全内容の一致を確認。
- 再構築assetsをexe隣へ置いたFuseゲームで `system / opening` 到達（画像・音声の非同期読込み）を確認。
- 配布フォルダに同梱したツールから、更新版player適用済みの既存原作フォルダを入力する経路も検証。
- tests/test_build_assets.py と test_extract_original.py の計7テスト成功。圧縮の4モード、PNG/DDS保存、フォルダ入力、不足素材、上書き拒否、レシピのパス、SFX、日本語名を含む。
- 素材なし配布ビルド成功。exe内にassetsを含まず、構築ツール・レシピ・必要Pythonコード・ライセンスを別添。

実OSでの検証はWindows。macOS/Linuxも同じPython実装を使うが、実機検証は未実施。
