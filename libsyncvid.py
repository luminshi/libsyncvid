from time import sleep
import subprocess
import json
import os
import threading
from config import mpv_ipc_socket_path


class VideoController:
    def __init__(self, connection):
        self.connection = connection
        self.FNULL = open(os.devnull, 'w')

    def __del__(self):
        self.FNULL.close()

    def get_buffering_status(self):
        if self.__getter("paused-for-cache"):
            return "buffering"
        else:
            return "buffered"

    def get_time_pos(self):
        return self.__getter("time-pos")

    def set_time_pos(self, time_pos_val):
        # a.k.a. seek()
        self.__setter("time-pos", time_pos_val)

    def get_play_status(self):
        if self.__getter("pause"):
            return "pause"
        else:
            return "play"

    def set_play_status(self, play_status):
        if play_status == "pause":
            self.__setter("pause", "true")
        else:
            self.__setter("pause", "false")

    def __getter(self, property_name):
        cmd_str = '{ "command": ["get_property", "' + property_name + '"] }'
        p1 = subprocess.Popen(["echo", cmd_str],
                              stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["socat", "-", mpv_ipc_socket_path],
                              stdin=p1.stdout, stdout=subprocess.PIPE, stderr=self.FNULL)
        p1.stdout.close()
        output, err = p2.communicate()

        if err is not None:
            exit(-1)
        elif output == '':
            print("connection refused")
            exit(-2)
        else:
            return json.loads(output)['data']

    def __setter(self, property_name, property_val):
        p1 = subprocess.Popen(["echo",
                               '{ "command": ["set_property", "' + property_name + '", ' + str(property_val) + '] }'],
                              stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["socat", "-", mpv_ipc_socket_path],
                              stdin=p1.stdout, stdout=subprocess.PIPE, stderr=self.FNULL)
        p1.stdout.close()
        p2.communicate()


# monitors for the video playback state changes when runs as a syncvid server
class VideoServer(VideoController):
    """
    Query mpv socket to monitor for playback status change
        * is the video paused or not
        * video playback position diff
    """
    play_status = "pause"
    exit_signal = False
    monitor_t = None

    def __init__(self, connection):
        self.FNULL = open(os.devnull, 'w')
        VideoController.__init__(self, connection)

    def __del__(self):
        self.FNULL.close()

    # server sends local play states to clients
    def start(self):
        # create and start a thread for __state_monitor()
        self.monitor_t = threading.Thread(target=self.__state_monitor)
        self.monitor_t.start()

    def stop(self):
        self.exit_signal = True
        self.monitor_t.join()

    def __state_monitor(self):
        # make sure the client state is synced with the server
        while_counter = 0
        while not self.exit_signal:
            # check server's playing status change, and change client's playing status if true
            if self.play_status != self.get_play_status():
                print("play status changed")
                self.play_status = self.get_play_status()
                self.__change_client_status()

            # send a heartbeat signal for every 5 secs.
            if while_counter > 500:
                # send the signal to keep the tcp connection alive
                self.connection.send({'action': 'heartbeat'})
                # reset while counter
                while_counter = 0

            while_counter += 1
            sleep(0.01)

        # signal client that the entire program has exited.

    def __change_client_status(self):
        # first sync time-pos with client
        time_pos = self.get_time_pos()
        self.connection.send({'action': 'set', 'property': 'time-pos', 'property-val': time_pos})

        if self.play_status == "play":
            print("play status changed to PLAY")

            # temporarily pause the local playback and set the time_pos
            self.set_play_status("pause")
            self.set_time_pos(time_pos)

            # then check whether client is ready to play
            client_ready = False
            while not client_ready:
                # ask if the client is ready
                self.connection.send({'action': 'get', 'property': 'paused-for-cache'})
                # receive buffering status from the client
                client_data = self.connection.recv()
                print("received data from client: {}".format(client_data))

                # if client is ready to play; buffered
                if client_data['data'] == "buffered":
                    client_ready = True
                else:  # the client is still buffering
                    sleep(2)

            # command the client to play vid
            self.connection.send({"action": "set", "property": "paused", "property-val": False})
            # unpause the local playback
            self.set_play_status("play")
        else:
            print("play status changed to PAUSE")
            # command the client to pause vid
            self.connection.send({"action": "set", "property": "paused", "property-val": True})


class VideoClient(VideoController):
    exit_signal = False
    state_syncer_t = None

    def __init__(self, connection):
        VideoController.__init__(self, connection)

    # client receives play states from server
    def start(self):
        self.state_syncer_t = threading.Thread(target=self.__state_syncer)
        self.state_syncer_t.start()

    def stop(self):
        self.exit_signal = True
        pass

    # receives playing state from server
    def __state_syncer(self):
        server_data = self.connection.recv()
        while not self.exit_signal:
            print("data received: {}".format(server_data))

            data_to_send = None
            if server_data["action"] == "get":
                if server_data["property"] == "paused-for-cache":
                    data_to_send = {"data": self.get_buffering_status()}
            elif server_data["action"] == "set":
                if server_data["property"] == "time-pos":
                    print("seeking data")
                    self.set_time_pos(server_data["property-val"])
                elif server_data["property"] == "paused":
                    paused = server_data['property-val']
                    print("changing paused status to: {}".format(paused))
                    if paused:
                        self.set_play_status("pause")
                    else:
                        self.set_play_status("play")
            elif server_data["action"] == "heartbeat":
                pass
            else:
                print("unknown server request action: {}".format(server_data))
                pass

            if data_to_send is not None:
                self.connection.send(data_to_send)

            # pause to receive data
            server_data = self.connection.recv()
