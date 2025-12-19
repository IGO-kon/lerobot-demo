Forked the `read_write.py` from [Waveshare's SDK Python demo](https://files.waveshare.com/wiki/Bus-Servo-Adapter-(A)/STServo_Python.zip)

Prereqs:
- Download/extract the Python SDK from above
- Place the robots.py (along with the 2 .json calibration files) alongside other python examples
- Tested with Python 3.13.11, use pyenv/venv if necessary
- Install pip requirements of the SDK: `pip pip install -r requirements.txt`
- Modify robots.py (at the `devices` dict) to specify `DEVICENAME` of both robots. For me, this was /dev/ttyACM0 and /dev/ttyACM1
- Run `python robots.py`

Gemini/AI helped with the `robots.py` demo, but more like a peer-programming session, where I edited/fixed/reviewed everything it wrote. 
Generally, following [Fedora's proposed AI guidelines](https://communityblog.fedoraproject.org/council-policy-proposal-policy-on-ai-assisted-contributions/) for responsible use.
