# 0111: カテジナを正式名ナタリアへ統一

- 日付: 2026-10-08
- 状態: 適用済み

原作の内部名「カテジナ」を、移植側では正式名「ナタリア」に統一する。
キャラクター番号と選択順は変更しない。

## 変更

- assets/characters、data/characters、data/_conversion/characters のディレクトリを移動。
- 各サポートの所有キャラ別定義をナタリア.ltonへ移動し、media参照とsupportOwnerを更新。
- キャラ選択、システム一覧、ストーリー対戦相手、検証スクリプトを更新。
- names.pyの正式名変換とstory.pyの一覧を更新。convert.pyはキャラクターのnameフィールドも正式名で出力。
- 原作の.player、抽出元JSON名を示すコメント、過去の調査記録は内部名のまま維持。

## 確認

- owner_supports.planによる全10キャラの再生成結果が現在の定義と一致。
- sierra-aim: ナタリアを含む全10キャラの読み込み・実行が成功。
- combat-flow: ナタリアの素材を含む戦闘検証。
