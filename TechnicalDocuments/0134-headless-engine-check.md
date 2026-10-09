# CIの互換性チェックを画面なしで実行

Actions run 37889468424ではコンパイル成功後のVM起動で失敗した。
ログは `Unable to create renderer` と `1.1.0 - GDI Generic` を示している。
Windows runnerの描画環境不足であり、シグネチャ不一致のエラーではない。

check.ps1のテスト用confでwindow/graphics/audioのモジュール初期化を無効化する。
visible=falseのウィンドウでは描画コンテキスト作成を回避できない。
エンジンのAPI登録はモジュールのデバイス初期化とは独立しているため、
API登録とコンパイル済みコードの実行・成功マーカーの検査は維持される。
ゲーム本体のconfやエンジン側のソースは変更しない。

指定リリースのコンパイラ/VMで、SDL_VIDEODRIVERとSDL_AUDIODRIVERを
存在しないドライバ名にした状態でもチェックが成功することを確認した。
GitHub上の再確認はこの変更をpushした後に行う。
