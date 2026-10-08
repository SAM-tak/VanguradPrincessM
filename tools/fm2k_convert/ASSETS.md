# 原作から assets を構築する

Python 3.10以降を使用します。Windows・macOS・Linux共通の手順です。
Mac/Linuxでは、必要に応じて `python` を `python3` に読み替えてください。
OS管理のPythonへ追加インストールできない環境では、仮想環境を使います。

```sh
python3 -m venv .asset-env
.asset-env/bin/python -m pip install -r asset-builder/requirements.txt
.asset-env/bin/python asset-builder/build_assets.py /path/to/vanpri108.exe assets
```

配布exeと同じフォルダで、次を実行します。

```sh
python -m pip install -r asset-builder/requirements.txt
python asset-builder/build_assets.py /path/to/vanpri108.exe assets
```

Windowsでも手動解凍は不要です。パスに空白がある場合は引用符で囲んでください。
既に解凍してある場合は、原作のフォルダを指定できます。

```sh
python asset-builder/build_assets.py /path/to/vanpri108 assets
```

`.7z` も指定できます。フォルダは原作 `.kgt` が一つだけ含まれるものを指定してください。

完了後はゲームを起動できます。処理は原作exeを実行せず、画像・音声だけを取り出します。
配布された技定義やパレットデータは変更しません。Windows用の原作exe/DLLは解凍対象外です。
7-Zipコマンド、Wine、.NETは不要です。

既存の assets は上書きしません。再構築する場合は、まず別の名前（例: assets-new）で
構築し、成功を確認してから置き換えてください。失敗時は不完全な assets を公開しません。

この配布版の `assets-recipe.json` とセットで使ってください。原作にない素材が必要な場合や
異なる原作を指定した場合は、不足するファイル名を表示して終了します。

## 開発リポジトリから使う場合

```sh
python -m pip install -r tools/fm2k_convert/requirements.txt
python tools/fm2k_convert/build_assets.py vanpri108.exe build/assets
```

素材配置を変更した開発者は、配布前に照合用一覧を更新します。この一覧には素材の内容を
含めず、内容のハッシュと配置先だけを記録します。

```sh
python tools/fm2k_convert/build_assets.py assets tools/fm2k_convert/assets-recipe.json --write-recipe
```
