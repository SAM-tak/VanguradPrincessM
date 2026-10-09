# Windowsコンパイラの日本語出力パス

Actions run 37913211677ではheadlessのVM互換性チェック、素材ツールのexe化、
ゲーム全体のコンパイルが成功した後、`data/characters/あやね/cpu.lton` がないとして失敗した。

lhat-love v12.0.0-alpha.1のBoot.cppでは、PhysFSから得たUTF-8パスを
`_mkdir`、`fopen`、`std::filesystem::path(std::string)` にそのまま渡している。
WindowsのANSIコードページがUTF-8以外だと出力パスが文字化けする。
この開発PCはGetACP()が65001のため、通常実行では問題が現れなかった。

同じリリースのlovec.exeをbuild以下へコピーし、検証用コピーのmanifestだけを
`activeCodePage=en-US` に変更して、`data/あやね/cpu.lton` を一つコンパイルした。
終了コードは0、出力数も1だったが、ディレクトリが `ã‚ã‚„ã­` となり、期待するパスは存在しなかった。
ゲームの定義やスレッド数によらず再現する。

根本修正はlhat-love側で行う。UTF-8パスを明示的にUTF-16へ変換し、
Windowsの `_wfopen` / `_wmkdir` やUTF-8を明示するfilesystem変換を使う。
ASCII以外の出力先ルートも含めて対象箇所を調べ、非UTF-8環境のCIで出力パスを検証する。
このコンテキストではエンジン側ソース・配布バイナリを変更しない。

ゲーム側のcheck.ps1には日本語パスを追加し、コンパイラの終了コードだけでなく
期待する出力ファイルの存在も確認する。修正版エンジンを公開したらengine-release.jsonを更新する。
文字化けしたファイル名の事後修正やrunner全体のロケール変更による回避は行わない。

## 解決

lhat-love v12.0.0-alpha.2で修正済み。engine-release.jsonを同タグへ更新した。
alpha.2のlovec.exeのコピーに `activeCodePage=en-US` のmanifestを追加してcheck.ps1を実行し、
`data/あやね/cpu.lton` が正しいパスに出力されることを確認した。
