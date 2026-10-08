# 配布exeと外部assets

## 配布構成

既定の `tools/dist.ps1` はコードと実行用 data のみを Fuse する。assets、skills、_conversion、data.lton、support-source.lton は含めない。生成済みサポートパレットなど data 配下の実行用PNGは含める。

```text
VanguardPrincess/
  VanguardPrincess.exe
  エンジンのDLL
  assets/  ← 利用者が原作から抽出・変換したもの
```

外部 assets は配布版のマニフェストと一致する変換結果が必要。元画像の抽出だけでなく共有化・所有先整理・サポート画像統合まで行う。一括抽出の利用者向けUIは今回の変更には含まない。

```powershell
# 配布用（素材なし）。VS Codeの既存ビルドタスクもこの既定値を使用。
pwsh tools/dist.ps1
# 自前ビルド用（素材を含む）。
pwsh tools/dist.ps1 -IncludeAssets
```

再ビルドは出力フォルダ直下の assets を保持する。したがって素材なし配布で渡すのは生成exeとDLLであり、利用者が置いた assets を含む出力フォルダ全体を無条件に配布する処理ではない。

## マウント

`src/media.lh` をゲームの load 冒頭、先読み開始前に呼ぶ。ソース実行や素材入りFuseで assets が既に見えていればそのまま使う。

素材なしFuseでは `getSourceBaseDirectory()` を一時的にルートへ追加検索としてマウントし、そこから assets サブディレクトリを仮想 assets へ別途マウントした後、親ディレクトリを解除する。最終的に外部から公開するのは assets のみ。実行時のカレントディレクトリには依存しない。親の一時マウント中にゲームのロードやタスクを実行しない。

mount の相対パス解決は実ディレクトリと引数を連結するため、親を別名の仮想パスへマウントしてからその別名付きサブパスを mount に渡す方式は使わない。

assets がない場合は必要な配置を示すエラーを出す。正常にマウントしたディレクトリはゲーム中維持し、ワーカーの画像・音声読み込みにも使う。コード側の assets/... 参照や metadata の data/... 解決は変更しない。

## 検証

- `tools/test-external-media.ps1`: VM-onlyエンジンへ実際にFuseし、素材なし時の案内、exe隣のassets、異なるカレントディレクトリ、内蔵data優先、親ディレクトリ解除、素材同梱オプションを確認。
- パッケージ内の assets、_conversion、skills、変換用data.ltonとsupport-source.ltonの除外を確認。
- 実ゲームのコード・dataをFuseし、exe隣のassetsから非同期ロードして `system / opening` 到達を確認（`build/fused-game-smoke.log`）。
- 配布ビルド成功。230エントリー、assets 0、生成パレット14枚。exe約5.7MiB。

使用した lhat-love は mount/unmount 追加後のビルド。今回 lhat-love / 言語コアのソース変更は行っていない。
