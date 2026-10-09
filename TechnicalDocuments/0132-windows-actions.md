# Windows配布のGitHub Actions

`.github/workflows/windows.yml` はmainへのpush、vタグ、pull request、手動実行に対応。
Windows 2022 x64とPython 3.11.9を使用する。成果物はActionsの
`VanguardPrincess-windows-x64` ZIPから取得する。Releaseの自動公開は行わない。

エンジンは `tools/engine-release.json` の指定に従い、lhat-love
v12.0.0-alpha.2のrelwithdebinfo（コンパイル用）とvmonly-shipping（配布用）を取得。
SHA256を照合する。更新時はタグ、アセット名、ハッシュをまとめて変更する。

`dist.ps1 -Lovec <exe> -ShippingDirectory <dir>` によりエンジンのソースツリーを
持たずにビルド可能。明示指定時は時刻による再ビルドをしない。
既存のコンパイラ→VM実行チェックを維持し、互換性不一致は配布生成前に失敗する。
従来の `-Love` 指定によるローカルエンジンビルドも維持。

Actionsは原作素材を取得せず、ゲーム定義と素材構築exeを同梱する。
check-distribution.ps1が素材・変換中間データ・デバッグ用フォントの混入を検査する。
依存ライセンスとエンジンのライセンス・build-infoも同梱する。

ローカルで同じ処理を実行する例（ダウンロード先は未作成であること）：

```powershell
./tools/download-engine.ps1
./tools/dist.ps1 -Lovec build/release-engine/compiler/lovec.exe -ShippingDirectory build/release-engine/runtime
./tools/check-distribution.ps1
```

GitHub上での実行には、前段の素材構築exe対応を含む未コミットファイルもpushする必要がある。

ローカル検証では実際のリリースZIPをダウンロード・照合し、そのバイナリで互換性チェックと
配布ビルドに成功。原作assetsを含めないコピーで配布検査、素材ツール7テスト、actionlintも成功。
GitHubホストのrunnerでの実行はpush後に確認する。
