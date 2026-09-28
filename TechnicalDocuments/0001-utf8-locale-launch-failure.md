# 0001: UTF-8 システムロケールで原作 exe が起動しない

- **日付**: 2026-09-28
- **状態**: 解決済み（外部マニフェストで起動確認）

## 状況

`vanpri108/ヴァンガードプリンセス/ヴァンガードプリンセス.exe`（格闘ゲームツクール2nd ランタイム、2002年ビルド）を起動すると、ロゴ表示後に以下のエラーで止まる。

```text
GameDemo Open error[�^�C�g��.demo]
```

（`タイトル.demo` の Shift-JIS バイト列が文字化けしたもの）

## 原因

- 開発機のシステム設定は「ベータ: ワールドワイド言語サポートで Unicode UTF-8 を使用」が有効。
  `HKLM\SYSTEM\CurrentControlSet\Control\Nls\CodePage` の `ACP` と `OEMCP` がどちらも `65001`。
  システムロケール（非 Unicode プログラムの言語）は `ja-JP`。
- exe は ANSI API（`CreateFileA` など）を使う古いアプリ。
- `.kgt` などのデータ内のファイル参照（例: `かえで.player`, `タイトル.demo`）は **Shift-JIS (CP932) のバイト列**。
- ACP が UTF-8 だと SJIS バイト列を UTF-8 として解釈する → 実ファイル名と一致しない → 読み込みに失敗。

## 試した対処

- **Locale Emulator 2.5.0.1**（`LEProc.exe -run`）— **効果なし**。同じエラーが出る。
  UTF-8 ベータ有効の環境では LE のコードページ差し替えが効かないと見られる。
- **exe 横に外部マニフェストを置き `activeCodePage=Legacy` を指定** — **成功**。
  Windows 10 1903 以降のアプリ単位コードページ指定機能。`Legacy` はシステムロケール（ja-JP → CP932）の ANSI コードページを使う指定。
  exe に埋め込みマニフェストがないので、外部マニフェストがそのまま読まれる。

`ヴァンガードプリンセス.exe.manifest`:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly manifestVersion="1.0" xmlns="urn:schemas-microsoft-com:asm.v1">
  <application>
    <windowsSettings>
      <activeCodePage xmlns="http://schemas.microsoft.com/SMI/2019/WindowsSettings">Legacy</activeCodePage>
    </windowsSettings>
  </application>
</assembly>
```

結果: オープニングデモが再生され、ゲーム内の日本語テキストも正しく描画される。

## 注意点

- **タイトルバーだけは文字化けしたまま**（`���@���K�[�h�v�����Z�X`）。ウィンドウタイトルの A→W 変換はプロセス単位の ACP ではなくシステム側の変換を通るためと見られる。見た目だけの問題で、実害なし。
- マニフェストを置いた後、exe の更新日時を現在時刻に変えてから起動した（Windows はマニフェストの有無を exe のパス＋タイムスタンプでキャッシュするため、その無効化）。この操作が必須だったかは未検証。exe の中身は変えていない。元の更新日時は `2002-04-04 19:44:38`。
- ゲームはウィンドウが非アクティブだと進行が止まる。バックグラウンドから起動した場合は前面に出す必要がある。
- ゲームは二重起動を防いでいる。古いインスタンスが残っていると、新しい方が exit code 1 で即終了する。
- Locale Emulator は不要になった。プロジェクト直下の `Locale.Emulator.2.5.0.1/` は `.gitignore` に追加済み。

## 決定

- 原作 exe・データの中身には手を入れない。
- 原作は外部マニフェスト（上記）で起動する。システムの UTF-8 ベータ設定はそのまま残す。

## 移植への影響（lhat-love 側）

- `.kgt` / `.player` / `.stage` / `.demo` 内の文字列は Shift-JIS 前提で扱う。
- ローダーで CP932 → UTF-8 変換が必要。LÖVE 標準に CP932 デコーダーはないので、自前の変換テーブルか iconv 相当を用意する。
- ファイル名解決は変換後の UTF-8 名で行う（ディスク上の実ファイル名は UTF-16 で保存されていて、エクスプローラー上は正しく表示される）。
- 英語圏での呼び名は「Fighter Maker 2nd (FM2K)」。フォーマット解析資料を探すときのキーワード。
