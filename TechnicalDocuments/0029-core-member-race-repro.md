# 0029: LÖVE を使わないメンバー参照競合の再現

- **日付**: 2026-10-04
- **状況**: 0028 の複数ワーカーでの破損を、言語コア単独で再現して修正依頼する。
- **結果**: L^ CLI だけの20行で、別ワーカーの値を読む不具合を再現。LÖVE・画像・音声・LTON・チャネル・ゲーム素材は不要。

## コア側への修正依頼

`std.task` の2ワーカーで同じ閉包を実行すると、ワーカー内で作成したローカルテーブルの `own.tag` が、別ワーカーの値を返します。各ワーカーはそれぞれ `{ tag = 111 }` / `{ tag = 222 }` を作り、その後は変更せず読むだけです。結果も数値のみなので、大きいデータの移譲は再現条件ではありません。

再現コード: [tests/task-member-race.lh](../tests/task-member-race.lh)。これを単独の `.lh` ファイルとしてコピーし、通常の `lhat.exe` で実行できます。

```powershell
& C:/Users/Owner/source/repos/lhat/build/release/lhat.exe tests/task-member-race.lh
```

期待値は A=111 / B=222、正常終了。実測の一例:

```text
worker A: expected=111 actual=111; worker B: expected=222 actual=111
tests/task-member-race.lh: error: line 20: cross-worker member read
```

逆向き（A が222を読む）も発生。終了コードは1。

## 比較結果

| 条件 | 実測 |
| --- | --- |
| 2ワーカー、`own.tag` | 10/10回で誤読、exit 1 |
| `std.task.start(1)` だけに変更 | 3/3回で正常、exit 0 |
| 2ワーカーのまま `own["tag"]` に変更 | 3/3回で正常、exit 0 |

[実行ログ](evidence/0029-task-member-race.txt)。比較を繰り返すスクリプトは `tools/test-task-member-race.ps1`（`-Lhat` で実行ファイルを指定可能）。競合なので、修正後や別マシンでの単発成功だけでは解消判定しないこと。

## 調べてほしい箇所

- `lhat/src/vm.c:1163` の GETMEMBER と `:1195` の CALLMEMBER。共有 chunk の `member_caches` を検査後に再読している。
- `lhat/src/vm_member.c:1011` 付近。`answered` / `version` / `index` / `from_definition` の同期なし更新。
- `lhat/src/vm.c:264` 付近の説明は「キーの再確認で混在しても安全」としているが、別ワーカーの表に同名キーがある場合、所有する表の取り違えは防げない。非atomicな共有フィールドの並行読み書き自体も検討が必要。

まずキャッシュのマシン単位化などでこの再現を回帰テストとして通し、参照先の寿命・GETMEMBER / CALLMEMBER 双方の扱いを確認してほしい。単純なローカル変数へのコピーだけでは同期と寿命の問題を解決できない。

この最小ケースで確定したのは **L^ コア単独でのワーカー間誤読**。ゲームで ASAN が検出した二重解放との因果関係まで確定するには、コア修正後にゲーム側の2ワーカー試験も再実行する必要がある。

## 検証環境・今回の変更範囲

- Windows x64、`C:/Users/Owner/source/repos/lhat/build/release/lhat.exe`。
- lhat HEAD: `e31d1d69196fc1c4f1d907b1ea1d6d244e0b864e`。作業ツリーには開発中の所有権移譲変更あり。クリーンな同コミットだけでの再現を意味しない。
- CLI SHA256: `6FE082CD1DE3FC3559F2069040CF68CE4633942E863189282DCBE256CF76C721`。
- 今回は言語コアを編集・修正せず、既存CLIで実行。再現コード・比較スクリプト・記録をゲームリポジトリに追加した。
- ゲームのワーカー数は1本のまま維持。

## 修正後の再検証（2026-10-04）

ユーザーによるコア修正と LÔVE 再ビルド後に再検証。`vm.c` のキャッシュ参照先は共有 chunk から `m->member_caches` に変更されている。HEAD は同じで、修正はローカルの作業ツリーにある。

- 最小再現: 2ワーカーの `own.tag` が **10/10回正常**。1ワーカーおよび添字アクセスの比較も各3/3回正常。[ログ](evidence/0029-task-member-after-fix.txt)
- ゲーム: `src/resource.lh` を `std.task.start(2)` に変更。`tools/test-async.ps1` を **3回実行し、すべてexit 0**。読み込み中のESC、タイトルへ戻る、再選択、2キャラの試合開始、600更新の試合描画、欠損素材のエラー処理と終了を通過。全回で同期フォールバック0件。
- 実行ログ: [1回目](evidence/0029-game-two-workers-1.txt)、[2回目](evidence/0029-game-two-workers-2.txt)、[3回目](evidence/0029-game-two-workers-3.txt)。以前のクラッシュ経路は今回再現しなかった。
- テストソースの require が `../main.lh` などに変更されていたため、ルートへコピーする実行スクリプトで相対パスを補正した。最初の起動失敗はこの参照パスの問題で、ワーカーの失敗ではない。
- **2ワーカー設定を採用して維持する。** 今回は通常のフル版での検証で、ASAN・VM-only・全キャラ総当たりは再実施していない。

検証したバイナリの SHA256:

- lhat.exe: `A515C4B3093BA1E0ED0BA1D53C6B74ABB52C52E7E3EE718ABB9360BCB0649B48`
- love.dll: `EDF2EC901B075C5B6C51B852B9A5403C1F520D1E41A50C72EA080F3CFC9E2A03`
