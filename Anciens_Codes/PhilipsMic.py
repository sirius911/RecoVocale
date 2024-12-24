import asyncio
import pywinusb.hid as hid
import time
import threading

class PhilipsMic:
    def __init__(self, loop, on_no_touch=None, on_rec_push=None, on_play_push=None, on_rew_push=None, on_next_push=None, on_f1_push=None, on_f2_push=None, on_f3_push=None):
        self.vendor_id = 0x0911
        self.product_id = 0x0c1c
        self.loop = loop
        self.connected = False
        self.device = None
        self.on_no_push = on_no_touch
        self.on_rec_push = on_rec_push
        self.on_play_push = on_play_push
        self.on_rew_push = on_rew_push
        self.on_next_push = on_next_push
        self.on_f1_push = on_f1_push
        self.on_f2_push = on_f2_push
        self.on_f3_push = on_f3_push

         # Internal state to track button status
        self.prev_data = None

        # self.monitor_thread = threading.Thread(target=self.monitor)
        # self.monitor_thread.daemon = True
        # self.monitor_thread.start()
        # Run the monitor task in the asyncio loop
        asyncio.run_coroutine_threadsafe(self.monitor(), self.loop)

    # def check_connection(self):
    #     all_hids = hid.HidDeviceFilter(vendor_id=self.vendor_id, product_id=self.product_id).get_devices()
    #     if all_hids:
    #         self.device = all_hids[0]
    #         self.connected = True
    #     else:
    #         self.device = None
    #         self.connected = False

    async def check_connection(self):
        all_hids = hid.HidDeviceFilter(vendor_id=self.vendor_id, product_id=self.product_id).get_devices()
        if all_hids:
            if not self.connected:
                self.device = all_hids[0]
                self.connected = True
                self.connect()
        else:
            if self.connected:
                self.device = None
                self.connected = False
                self.disconnect()
                print("SpeechMike non trouvé. En attente de connexion...")

    def connect(self):
        if self.connected and self.device:
            self.device.open()
            self.device.set_raw_data_handler(self.on_data_handler)
            print("SpeechMike connecté")

    def disconnect(self):
        if self.device:
            self.device.close()
            self.connected = False
            # print("SpeechMike déconnecté")

    def on_data_handler(self, data):
        # print(f"Received data: {data}")
        # Interpréter les données reçues
        if data != self.prev_data:  # Check if the data has changed
            self.prev_data = data
            # Bouton REC appuyé
            if data == [0, 128, 0, 0, 0, 0, 0, 0, 0, 1]:
                print("Bouton REC appuyé")
                self.on_rec_push()
            elif data == [0, 128, 0, 0, 0, 0, 0, 0, 0, 4]:
                print("Bouton Play appuyé")
                self.on_play_push()
            elif data == [0, 128, 0, 0, 0, 0, 0, 0, 2, 0]:
                print("Bouton F1 appuyé")
                if self.on_f1_push:
                    self.on_f1_push()
            elif data == [0, 128, 0, 0, 0, 0, 0, 0, 0, 0]:
                print("Boutons relachés")
                if self.on_no_push:
                    self.on_no_push()
            else:
                print(f"Received data: {data}")

    async def monitor(self):
        while True:
            await self.check_connection()
            await asyncio.sleep(1)

    # def monitor(self):
    #     while True:
    #         self.check_connection()
    #         if self.connected:
    #             print("SpeechMike connecté")
    #             self.connect()
    #             while self.connected:
    #                 time.sleep(1)
    #                 self.check_connection()
    #                 if not self.connected:
    #                     self.disconnect()
    #                     print("SpeechMike déconnecté")
    #         else:
    #             print("SpeechMike non trouvé. En attente de connexion...")
    #             time.sleep(1)
