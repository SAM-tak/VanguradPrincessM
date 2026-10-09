# 開発用フォントの配置と配布除外

NotoSansMonoCJKjp-Regular.otfをassetsからdataへ移し、原作素材の抽出とは独立させる。
フォントはリポジトリで管理し、ライセンスはlicenses/NotoSansCJK-OFL.txtに置く。

main.lhのdebugTextはfused実行では直ちに戻り、フォントをロードせず、デバッグ文字を描画しない。
ソース実行では従来通り必要時にロードする。ゲーム本編の文字は原作画像を使うため影響しない。
package-game.ps1はこのフォントを除外する（IncludeAssets指定時も同様）。
デバッグキーなど、それ以外の操作仕様は変更していない。
