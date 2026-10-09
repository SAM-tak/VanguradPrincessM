# Python不要の素材構築ツール

Windows配布物にPyInstaller製の `BuildAssets.exe` を同梱する。
Python、Pillow、py7zrとそのネイティブ依存、素材配置レシピを内蔵したconsole/onefile形式。
原作の画像・音声は内蔵しない。入力と出力は従来のCLIと同じ。

`tools/dist.ps1` は既存配布物を削除する前に `tools/build-asset-builder.ps1` を実行する。
専用venvをbuild以下に作り、requirements-build.txtを導入してfreeze_builder.pyを実行する。
ビルド側にはPythonが必要だが、利用者側には不要。依存ライセンスも配布物に添付する。

macOS/Linuxでもfreeze_builder.pyをそのOSのPython環境で実行できる設計。
ただしWindowsからクロスビルドはできず、OS・CPU別の生成と実機検証が必要。
Linuxはビルド環境のglibcなどにも依存するので、対応する最古の環境で生成する。
今回の配布への組み込み・実行検証はWindowsのみ。

ビルド構成はPython 3.11.9 / PyInstaller 6.22.3 / Pillow 12.3.0 / py7zr 1.1.3。
onefileの起動時には内蔵ランタイムが一時展開される。生成されるexeは約18MB。

検証ではPythonをPATHから除外し、PYTHONPATHも空にして単体exeから原作vanpri108.exeを処理。
埋め込みレシピを使用して8,492ファイルを生成し、全件の内容ハッシュ照合が成功した。
素材構築・SFX抽出の既存7テストも成功。
