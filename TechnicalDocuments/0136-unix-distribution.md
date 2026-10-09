# Linux / macOS 配布

`.github/workflows/distribution.yml`（旧 windows.yml）をmatrix化し、
Windows x64（windows-2022）、Linux x64（ubuntu-24.04）、macOS arm64（macos-15）、
macOS x64（macos-15-intel）で同じスクリプトを実行する。エンジンはlhat-love
v12.0.0-alpha.2の各プラットフォーム版を `engine-release.json` の `platforms` で固定する。

## 配布構成

外部 assets は `getSourceBaseDirectory()` の隣に置く（[0128](0128-external-distribution-assets.md)）。
各OSの起動形式はこれを満たすよう選び、`tools/fuse-game.ps1` にまとめた。

- Windows: 従来どおり `love.exe` に `.love` を連結した `VanguardPrincess.exe` とDLL。
- Linux: `bin/love` に `.love` を連結した `VanguardPrincess` と `lib/`。
  リリースのRPATHは `$ORIGIN/../lib` なので、連結前にpatchelfで `$ORIGIN/lib` へ書き換える。
  glibc・GLドライバはホスト側（Ubuntu 24.04相当以降）。
- macOS: `lhat-love.app` は改変せず同梱し、隣に `VanguardPrincess.love` と
  `VanguardPrincess.command` を置く。launcherは `love --fused VanguardPrincess.love` を実行する。

macOSでMach-Oへ連結すると署名が `__LINKEDIT` の外のデータで無効になり、arm64では起動できない。
上流LÖVEの `Contents/Resources/*.love` 探索はlhat-loveのBoot.cppにない。
仮にあってもsource baseがResources内になり、assetsを.appの外に置けない。
`--fused` でsource baseが `.love` の隣になり、fusedとしてsource baseのマウントも許可される。
Windows版エンジンで `love.exe --fused 別フォルダ/game.love` を実行し、
`.love` 隣のassetsを読めることを確認した。

公証していないため、利用者は配布フォルダの隔離属性を外す必要がある（ASSETS.mdに記載）。
upload-artifactは実行権限を保持しないので、Unix版は `tar.gz` にしてからアップロードする。

## 素材構築ツール

`BuildAssets` は各runnerのPython 3.11.9でPyInstallerにより生成する（[0131](0131-standalone-asset-builder.md)）。
venvのPythonは `bin/python`。クロスビルドはしない。

## 検査

- check.ps1: 各OSのコンパイラ/VMで互換性と日本語出力パスを確認。
- test-external-media.ps1: fuse-game.ps1で実際の起動形式を作り、素材なしの案内、
  外部assets、内蔵data優先、素材同梱を画面なしで確認。CIで全OS実行。
- check-distribution.ps1: OS別の必須ファイル、Unixの実行権限、macOSの `codesign --verify`。

ローカル検証はWindowsのみ（test-external-media、dist、check-distribution成功）。
Linux/macOSはActionsで確認する。
