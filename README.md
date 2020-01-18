# libsyncvid
To sync video playback status of two mpv processes.
Tested on MacOS and Ubuntu 18.04 only.

## Dependencies:
`python3`, `socat`, and  `mpv`

## Usages:

```
usage: syncvid.py [-h] (-s | -c serverIP) [-p PORT] video_path

sync video playback state between two (maybe more in the future) video players with low
latency.

positional arguments:
  video_path            the file path to a video file

optional arguments:
  -h, --help            show this help message and exit
  -s, --server          run program in server mode
  -c serverIP, --client serverIP
                        run program in client mode, requires server IP
  -p PORT, --port PORT  port to serve/connect with
```
