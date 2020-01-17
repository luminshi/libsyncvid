import argparse
import subprocess
from multiprocessing import Process

import dep.jsonsocket as jsonsocket

from libsyncvid import VideoServer, VideoClient
from config import *


def player_process(path):
    p1 = subprocess.run(["mpv", path, "--pause", "--no-config", "--hwdec=auto",
                         "--geometry=50%:50%", "--autofit=33%x33%",
                         "--input-ipc-server={}".format(mpv_ipc_socket_path)])


def main():

    # arg parser!
    parser = argparse.ArgumentParser(description="sync video playback state between "
                                                 "two (maybe more) video players with low latency.")
    # require users to run the program in either server or client mode.
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--server", action="store_true",
                       help="run program in server mode")
    group.add_argument('-c', "--client", metavar="serverIP", type=str,
                       help="run program in client mode, requires server IP")

    # get optional port to serve/connect with
    parser.add_argument("-p", "--port", type=int,
                        default=syncvid_port,
                        help="port to serve/connect with")

    # get video file path
    parser.add_argument("video_path", help="the file path to a video file")
    # server or client mode
    args = parser.parse_args()
    print("video path: {}".format(args.video_path))
    print("port: {}".format(args.port))

    # start video player
    mpv_proc = Process(target=player_process, args=(args.video_path,))
    mpv_proc.start()

    # launch the corresponding program.
    if args.server:
        # create server socket and wait for a client to connect
        server = jsonsocket.Server("0.0.0.0", args.port)
        print("the server started.")
        server.accept()
        print("a client connected.")

        # once connection is established, hand it off to VideoServer
        vs = VideoServer(server)
        vs.start()
        print("video server is now running.")
    else:
        # connect to a syncvid server
        serverIP = args.client
        # validate serverIP
        print(serverIP)
        client = jsonsocket.Client()
        client.connect(serverIP, args.port)

        # once connection is established, hand it off to VideoClient
        vc = VideoClient(client)
        vc.start()
        print("video client is now running.")

    # handle program exit
    # join mpv process.
    mpv_proc.join()
    print("exiting the program.")


main()
