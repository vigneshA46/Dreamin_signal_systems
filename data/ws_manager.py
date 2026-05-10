import threading
from dhanhq import marketfeed



class WSManager:

    def __init__(self, client_id, access_token):
        self.client_id = client_id
        self.access_token = access_token
        self.instruments = []
        self.feed = None

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):

        self.feed = marketfeed.DhanFeed(
            self.client_id,
            self.access_token,
            self.instruments,
            "v2"
        )

        while True:
            try:
                self.feed.run_forever()

                data = self.feed.get_data()

                if data:
                    self.on_message(data)

            except Exception as e:
                print("WS ERROR:", e)

    def subscribe(self, exchange, security_id):

        instrument = (exchange, security_id, marketfeed.Quote)

        if instrument not in self.instruments:
            self.instruments.append(instrument)

            if self.feed:
                self.feed.subscribe([instrument])

            print("SUBSCRIBED:", instrument)

    def on_message(self, data):
        # connect this to your engine
        print(data)