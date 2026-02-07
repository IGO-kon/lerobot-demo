
WaveshareのSDK Pythonデモ（[Waveshare's SDK Python demo](https://files.waveshare.com/wiki/Bus-Servo-Adapter-(A)/STServo_Python.zip)）から`read_write.py`をフォークしました。

前提条件:
- 上記リンクからPython SDKをダウンロード・解凍してください
- robots.py（および2つの.jsonキャリブレーションファイル）を他のPythonサンプルと同じ場所に配置してください
- Python 3.13.11でテスト済み。必要に応じてpyenvやvenvを使用してください
- SDKのpip要件をインストール: `pip install -r requirements.txt`
- robots.py内の`devices`ディクショナリで、両方のロボットの`DEVICENAME`を指定してください。私の場合は /dev/ttyACM0 と /dev/ttyACM1 でした
- `python robots.py` を実行してください。
