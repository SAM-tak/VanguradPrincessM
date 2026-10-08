# 追加41枚の所有先整理

ユーザー指定の画像を所有者ルールに追加し、既存の所有先訂正処理で移動した。以前のえこ独立パレット対応は維持。

| 所有者 | 指定枚数 | 配置 |
| --- | ---: | --- |
| ゆい | 1 | assets/characters/ゆい/images/1397.dds |
| えこ | 4 | assets/supports/えこ/images/ |
| シエラ | 8 | assets/supports/シエラ/images/ |
| ジュリエット | 8 | assets/supports/ジュリエット/images/ |
| かなえ | 11 | assets/supports/かなえ/images/ |
| ヒルダ（サポート） | 9 | assets/supports/ヒルダ/images/ |

ゆいの `9aeb81a5857a6a366666b90660d02be78cf60b4f.dds` は元の画像番号1397へ戻し、えり側の誤った同スロット参照を nil にした。`share_owners.txt` に記録。

サポート40枚は `support_media_owners.txt` に記録し、`organize_support_media.py --owned-only --apply` で12マニフェストを書き換えた。移動前後の SHA-256 は全40枚一致。他キャラや他サポートからの参照も維持する。これら4サポートへの独立パレット適用は今回行わない。

## えこの追加統合

`support_palettes.py --support えこ --apply` を再適用した。

- `c956d5005c5e873eea90810b8f10b3bd3f3c3f16.dds` と `d3081f18dead1cfb7c0afe2c84295d09c8f68907.dds` は色番号置換で既存画像と一致し、統合して削除。
- `b8cd2f5cfdb0e3726fbf66fc8b4ad18125e160a4.dds` と `e0b13844868e0c1a7720a0500ed3ea9e4f75ef9b.dds` は残す。
- 118枚から116枚へ、追加49,466バイト削減。パレットは引き続き14枚で追加不要。
- 更新対象は1404エントリー。全8色の全画素RGBA一致を検証。

## 検証

- 41枚すべて旧 shared 配置から除去。全実行用 images.lton の参照切れ0。
- 所有先整理・共有素材・独立パレットの Python テスト計10件成功。
- support-flow: 全250通りのサポート入力、固定ボス、CPU操作を含め成功。
- support-palettes: 全11キャラの全8色描画、パレット先読みを確認。
- 作業直前のローカル退避: `build/additional-media-before.zip`。
