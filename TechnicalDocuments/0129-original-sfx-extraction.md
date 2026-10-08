# 原作自己解凍7zをPythonから展開

`tools/fm2k_convert/extract_original.py` を追加。Windows用自己解凍プログラムを実行せず、7z部分を探して切り出し、py7zr 1.1.3で展開する。通常の7zにも対応。requirements.txtへ依存を追加した。

```sh
python -m pip install -r tools/fm2k_convert/requirements.txt
python tools/fm2k_convert/extract_original.py vanpri108.exe build/original
python tools/fm2k_convert/extract_original.py vanpri108.exe --list
```

## 実物の形式

手元の vanpri108.exe は181,784,539バイト。7z部分はoffset 140,288、181,644,251バイト。固定オフセットではなく、署名・開始ヘッダCRC・次ヘッダCRCと範囲を検証して検出する。

原作ゲームexeだけがBCJ2を使用しており、py7zrでは展開できない。FM2K素材はLZMAで別の圧縮ストリームにあるため、変換に不要なexe/DLLを対象から除いて展開できる。最初の「7z部分を切り出せば全ファイルをpy7zrで展開できる」という想定はこの点で修正した。CLIは除外するファイル名を表示する。

## 出力と検証

新しい出力ディレクトリだけを受け付け、既存ファイルは上書きしない。一時領域へ展開し、各ファイルのサイズ・CRCを確認してから出力先へ移す。アーカイブ内の絶対パス・親参照・リンク・重複パスを拒否。入力exeの起動は一切行わない。

py7zrにはファイルストリームを渡して逐次展開する。並列展開で未対応圧縮が発生した際、一部ワーカーが一時ファイルを保持してWindowsの削除エラーを引き起こしたため、逐次処理としている。

- 実物の48エントリー（ディレクトリ3、ファイル45）、487,619,184バイトを展開成功。
- kgt 1、demo 16、stage 7は既存ドナーとSHA-256一致。
- player 14のうち4は一致、10は既存ドナーに適用済みの更新版との差。解凍ツールは配布exeの内容をそのまま保存し、更新版への置換は行わない。
- tests/test_extract_original.py: 通常7z、偽署名付きSFX、末尾データ、日本語名、exe除外、一覧、上書き拒否、破損ヘッダ、危険パスの検証成功。

実物の実行検証はWindows上。Mac/Linuxで同じPythonコードを使用する設計だが、実OS上の検証は未実施。FM2K解析・assets生成は既存の後段パイプラインであり、今回のコマンドだけではassetsを生成しない。
