def auth():
    # Kraken KEY & SECRET
    key = ''
    secret = ''
    return key, secret

import aiohttp
import json
import time
import numpy as np
import datetime
import asyncio
import websockets
import urllib.parse
import hashlib
import hmac
import base64
from functools import partial
import requests

# Timestamp generation and conversion functions
stamp = lambda: int(time.time() * 1000000)
TrT = lambda u: datetime.datetime.fromtimestamp(u).strftime('%M:%S')

postage_stamp = lambda: int(time.time())
rightNow = lambda: datetime.datetime.fromtimestamp(int(time.time())).strftime('%I:%M:%S')


# This decorator extracts my current US Dollar balance
def USDollar(f):
    def Fetch(*a, **b):
        resp = f(*a, **b)
        if 'result' in resp.keys():
            if 'ZUSD' in resp['result'].keys():
                return float(resp['result']['ZUSD'])
        return None
    return Fetch

# Trading execution class
class KrakenAPI:

    def __init__(self, key, secret):
        self.key, self.secret = key, secret
        self.rest_url = 'https://api.kraken.com'
        self.session = requests.Session()
    
    # Encrypt private requests
    def signature(self, urlpath, data):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(self.secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()
    
    # Place a POST request to Kraken's Server
    def communicate(self, uri_path, data):
        headers = {}
        headers['API-Key'] = self.key 
        headers['API-Sign'] = self.signature(uri_path, data)             
        resp = self.session.post(self.rest_url + uri_path, headers=headers, data=data).json()
        return resp
    
    # Current Balance
    @USDollar
    def Balance(self):
        endpoint = '/0/private/Balance'
        msg = {
            'nonce': stamp()
        }
        resp = self.communicate(endpoint, msg)
        return resp

    # Cancels order
    def CancelOrder(self, pair, txid):
        endpoint = '/0/private/CancelOrder'
        msg = {
            'nonce': stamp(),
            'pair': pair,
            'txid': txid
        }
        resp = self.communicate(endpoint, msg)
        return resp


    # Places a limit buy order
    def LimitBuy(self, pair, price, volume, cl_ord_id):
        endpoint = '/0/private/AddOrder'
        msg = {
            'nonce':stamp(),
            'ordertype':'limit',
            'type':'buy',
            'price':price,
            'volume':volume,
            'pair':pair,
            'cl_ord_id':cl_ord_id
        }
        resp = self.communicate(endpoint, msg)
        return resp

    # Places a limit sell order
    def LimitSell(self, pair, price, volume, cl_ord_id):
        endpoint = '/0/private/AddOrder'
        msg = {
            'nonce':stamp(),
            'ordertype':'limit',
            'type':'sell',
            'price':price,
            'volume':volume,
            'pair':pair,
            'cl_ord_id':cl_ord_id
        }
        resp = self.communicate(endpoint, msg)
        return resp

    # Gets open orders
    def OpenOrders(self, cl_ord_id):
        endpoint = '/0/private/OpenOrders'
        msg = {
            'nonce':stamp(),
            'trades':True,
            'cl_ord_id': cl_ord_id
        }
        resp = self.communicate(endpoint, msg)
        return resp
    
    # Edits orders price and quantity
    def EditOrder(self, txid, volume, price):
        endpoint = '/0/private/AmendOrder'
        msg = {
            'nonce':stamp(),
            'txid': txid,
            'order_qty': volume,
            'limit_price': price
        }
        resp = self.communicate(endpoint, msg)
        return resp

    # Checks to see if limit order has filled
    def CheckFill(self, txid, cl_ord_id):
        time.sleep(2)
        x = self.OpenOrders(cl_ord_id)
        y = x['result']['open']
        if txid not in y.keys():
            return 'Filled'
        return 'Filling'



class Data:

    # Stores the highest bid/lowest ask, level2 orderbook, trading metrics, pnl, and balance
    khigh_bid = None
    klow_ask = None
    kprice = None
    storage = []
    cbids = {}
    casks = {}
    cbwap = None
    cbook = None
    cbsd = None
    obook_graph = None
    profit = []
    printer = '> Trading System'
    current_balance = 0
    entry_price = 0
    exit_price = 0
    gain_or_loss = 0

    # Extract AutoCorrelation Signal for Trading
    def AutoCorr(self, prices, lag=5):
        x = np.array(prices)
        a = x[lag:]
        b = x[:-lag]
        cv = np.cov(a, b)
        covar = cv[0, 1]
        vari = cv[0, 0]
        beta = covar / vari
        return beta

    # Checks to see if data feed has synced and is ready to run the system
    def Synchronize(self):
        if len(self.storage) > 20 and self.khigh_bid != None and self.klow_ask != None and self.obook_graph != None:
            self.cbsd = np.std(self.storage)
            return True
        else:
            self.printer = f'System data is loading: {21 - len(self.storage)}'
            return False

    # Fetches the highest bid/lowest ask from Kraken
    def PullKraken(self, resp):
        self.kprice = float(resp[1]['c'][0])
        self.khigh_bid = float(resp[1]['b'][0])
        self.klow_ask = float(resp[1]['a'][0])
    
    # Parses ticker data and level2 orderbook data
    def PullCoinbase(self, resp, coinLimit=50):
        if 'type' in resp.keys():

            # Stores ticker price data
            if resp['type'] == 'ticker':
                price = float(resp['price'])
                self.storage.append(price)

            # Stores the initial snapshot of the level2 orderbook
            if resp['type'] == 'snapshot':
                self.cbids = {float(price):float(size) for price, size in resp['bids']}
                self.casks = {float(price):float(size) for price, size in resp['asks']}
                self.OrderBookStats()

            # Updates the stored level2 orderbook
            if resp['type'] == 'l2update':
                for side, price, size in resp['changes']:
                    price, size = float(price), float(size)
                    if side == 'buy':
                        if size == 0:
                            if price in self.cbids.keys():
                                del self.cbids[price]
                        else:
                            self.cbids[price] = size
                    else:
                        if size == 0:
                            if price in self.casks.keys():
                                del self.casks[price]
                        else:
                            self.casks[price] = size
                self.OrderBookStats()

        if len(self.storage) > coinLimit:
            del self.storage[0]

    # Calculates volume summation to visualize orderbook
    def OrderBookStats(self, depth=40):
        bids = np.array(list(sorted(self.cbids.items(), reverse=True))[:depth])
        asks = np.array(list(sorted(self.casks.items()))[:depth])
        bw = np.sum(bids[:, 0]*bids[:, 1])/np.sum(bids[:, 1])
        aw = np.sum(asks[:, 0]*asks[:, 1])/np.sum(asks[:, 1])
        ratio = (np.sum(bids[:, 1]) - np.sum(asks[:, 1]))/(np.sum(bids[:, 1]) + np.sum(asks[:, 1]))
        bidp = bids[:, 0][::-1]
        bidv = np.cumsum(bids[:, 1])[::-1]
        askp = asks[:, 0]
        askv = np.cumsum(asks[:, 1])
        self.cbwap = 0.5*(bw + aw)
        self.cbook = ratio
        self.obook_graph = {'bp':bidp.tolist(), 'bv':bidv.tolist(), 'ap':askp.tolist(), 'av':askv.tolist()}

    # I developed a fluid limit order engine which battles other algorithms for the best bid/ask price
    async def XLimitBuy(self, session, pair, price, volume, cl_ord_id):

        # Place initial buy order
        order = self.api.LimitBuy(pair, price, volume, cl_ord_id)
        self.printer = json.dumps(order)

        # Extract transacton id
        txid = order['result']['txid'][0]
        c = 0.1
        t0 = postage_stamp()

        # Runs until limit order has been filled by editing the price by increments
        while True:
            filled = self.api.CheckFill(txid, cl_ord_id)
            if filled == "Filled":
                self.printer = f"Limit Buy has been filled {rightNow()} | {price}"
                self.entry_price = price
                break
            else:
                price = round(self.khigh_bid + c, 1)
                
                self.printer = f"Editing Limit Buy {rightNow()} | {price}"
                self.api.EditOrder(txid, volume, price)
            
            if postage_stamp() - t0 < 35:
                c += 0.1
            else:
                self.printer = f'Emergency Exiting {rightNow()} | {price}'
                c += 5.0
            await asyncio.sleep(0.2)

    # Limit sell order engine
    async def XLimitSell(self, session, pair, price, volume, cl_ord_id):

        # Place sell order
        order = self.api.LimitSell(pair, price, volume, cl_ord_id)
        self.printer = json.dumps(order)

        # Get transaction fee
        txid = order['result']['txid'][0]
        c = 0.1
        t0 = postage_stamp()

        # Loop until order has been filled by editing the price
        while True:
            filled = self.api.CheckFill(txid, cl_ord_id)
            if filled == "Filled":
                self.printer = f"Limit Sell has been filled {rightNow()} | {price}"
                break
            else:
                price = round(self.klow_ask - c, 1)
                
                self.printer = f"Editing Limit Sell {rightNow()} | {price}"
                self.api.EditOrder(txid, volume, price)
            self.exit_price = price

            if postage_stamp() - t0 < 35:
                c += 0.1
            else:
                self.printer = f'Emergency Exiting {rightNow()} | {price}'
                c += 5.0
            await asyncio.sleep(0.2)


# Main class
class Trader(Data):

    def __init__(self, exit_trade=8, host='0.0.0.0', port=8080):
        self.kraken_ws_url = 'wss://ws.kraken.com'
        self.cb_ws_url = 'wss://ws-feed.exchange.coinbase.com'
        self.exit_trade = int(60*exit_trade)
        key, secret = auth()
        self.api = KrakenAPI(key, secret)
        self.host = host
        self.port = port

    # Run the event loop to run system
    def ignition(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.starter())
        
    # Divides up the parallel tasks of running the websocket, running the strategy, and sending React.js data to visualize
    async def starter(self):
        
        # Server Initializer
        async def messenger():
            server = await websockets.serve(self.ServerFeed, self.host, self.port)
            await server.wait_closed()
        
        # Creates a session where all of the network connections originate from
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            #server = await websockets.serve(self.ServerFeed, self.host, self.port)

            # Start tasks for KrakenFeed and CoinbaseFeed
            tasks = [self.KrakenFeed(session), self.CoinbaseFeed(session), self.TradingStrat(session), messenger()]
            
            await asyncio.gather(*tasks)  # Gather tasks instead of using ensure_future
            
            #await server.wait_closed()  # Ensures the WebSocket server stays open

    # Kraken WebSocket data feed
    async def KrakenFeed(self, session):
        print("Connected To Kraken..........")
        async with session.ws_connect(self.kraken_ws_url) as conn:
            msg = {'event':'subscribe','pair':['XBT/USD'],'subscription':{'name':'ticker'}}
            await conn.send_str(json.dumps(msg))
            while True:
                resp = await conn.receive()
                resp = json.loads(resp.data)
                if type(resp) == list:
                    self.PullKraken(resp)
                await asyncio.sleep(0.001)
            
    # Coinbase WebSocket data feed
    async def CoinbaseFeed(self, session):
        try:
            print("Connected To Coinbase..........")
            async with session.ws_connect(self.cb_ws_url) as conn:
                msg = {'type':'subscribe','product_ids':['BTC-USD'], 'channels':['ticker', 'level2_batch']}
                await conn.send_str(json.dumps(msg))
                while True:
                    resp = await conn.receive()
                    resp = json.loads(resp.data)
                    self.PullCoinbase(resp)
                            
                    await asyncio.sleep(0.001)
        except:
            print("Reconnecting to Coinbase Socket")
            await asyncio.sleep(10)
            await self.CoinbaseFeed(session)
            
    # Trading Strategy
    async def TradingStrat(self, session):
        side = 'neutral'
        volume = 0.00005
        cl_ord_ida = "ClassOf2013-1994"
        cl_ord_idb = "ClassOf2013-1995"

        entryBalance = None
        exitBalance = None 

        t0 = postage_stamp()
        tv0 = postage_stamp()

        store_auto_corr_beta = []

        while True:
            if self.Synchronize():
                
                # Risk Management Exit
                if side == 'long' and self.entry_price > self.klow_ask + np.maximum(1.00, self.cbsd):
                    await self.XLimitSell(session, "XBTUSD", self.klow_ask, volume, cl_ord_idb)
                    await asyncio.sleep(2)
                    exitBalance = self.api.Balance()
                    side = 'neutral'
                    self.printer = f"Risk Management: Exited Long Position: {rightNow()}"
                    self.current_balance = exitBalance
                    #self.profit.append(exitBalance / entryBalance - 1.0)
                    self.profit.append(self.exit_price / self.entry_price - 1.0)
                    await asyncio.sleep(2)
                    t0 = postage_stamp()
                    tv0 = postage_stamp()

                # Time based profit tiers based on price volatility, lower level required to exit every two minutes
                if side == 'long' and (self.klow_ask*(1-0.0025))/(self.entry_price*(1+0.0025)) - 1.0 > 0:
                    await self.XLimitSell(session, "XBTUSD", self.klow_ask, volume, cl_ord_idb)
                    await asyncio.sleep(2)
                    exitBalance = self.api.Balance()
                    side = 'neutral'
                    self.printer = f"XTier: Exited Long Position: {rightNow()}"
                    self.current_balance = exitBalance
                    #self.profit.append(exitBalance / entryBalance - 1.0)
                    self.profit.append(self.exit_price / self.entry_price - 1.0)
                    await asyncio.sleep(2)
                    t0 = postage_stamp()
                    tv0 = postage_stamp()
                elif side == 'long' and postage_stamp() - t0 > 60*2 and self.klow_ask > self.entry_price + 3.0*self.cbsd:
                    await self.XLimitSell(session, "XBTUSD", self.klow_ask, volume, cl_ord_idb)
                    await asyncio.sleep(2)
                    exitBalance = self.api.Balance()
                    side = 'neutral'
                    self.printer = f"Tier 1: Exited Long Position: {rightNow()}"
                    self.current_balance = exitBalance
                    #self.profit.append(exitBalance / entryBalance - 1.0)
                    self.profit.append(self.exit_price / self.entry_price - 1.0)
                    await asyncio.sleep(2)
                    t0 = postage_stamp()
                    tv0 = postage_stamp()
                elif side == 'long' and postage_stamp() - t0 > 60*4 and self.klow_ask > self.entry_price + 2.0*self.cbsd:
                    await self.XLimitSell(session, "XBTUSD", self.klow_ask, volume, cl_ord_idb)
                    await asyncio.sleep(2)
                    exitBalance = self.api.Balance()
                    side = 'neutral'
                    self.printer = f"Tier 2: Exited Long Position: {rightNow()}"
                    self.current_balance = exitBalance
                    #self.profit.append(exitBalance / entryBalance - 1.0)
                    self.profit.append(self.exit_price / self.entry_price - 1.0)
                    await asyncio.sleep(2)
                    t0 = postage_stamp()
                    tv0 = postage_stamp()
                elif side == 'long' and postage_stamp() - t0 > 60*6 and self.klow_ask > self.entry_price + self.cbsd:
                    await self.XLimitSell(session, "XBTUSD", self.klow_ask, volume, cl_ord_idb)
                    await asyncio.sleep(2)
                    exitBalance = self.api.Balance()
                    side = 'neutral'
                    self.printer = f"Tier 3: Exited Long Position: {rightNow()}"
                    self.current_balance = exitBalance
                    #self.profit.append(exitBalance / entryBalance - 1.0)
                    self.profit.append(self.exit_price / self.entry_price - 1.0)
                    await asyncio.sleep(2)
                    t0 = postage_stamp()
                    tv0 = postage_stamp()
                elif side == 'long' and postage_stamp() - t0 > self.exit_trade:
                    await self.XLimitSell(session, "XBTUSD", self.klow_ask, volume, cl_ord_idb)
                    await asyncio.sleep(2)
                    exitBalance = self.api.Balance()
                    side = 'neutral'
                    self.printer = f"Out of time: Exited Long Position: {rightNow()}"
                    self.current_balance = exitBalance
                    #self.profit.append(exitBalance / entryBalance - 1.0)
                    self.profit.append(self.exit_price / self.entry_price - 1.0)
                    await asyncio.sleep(2)
                    t0 = postage_stamp()
                    tv0 = postage_stamp()
                else:
                    pass

                store_auto_corr_beta.append(self.AutoCorr(self.storage))

                if side == 'neutral':
                    self.gain_or_loss = 0
                    self.printer = f"Not currently in a position: {rightNow()}"
                
                if len(store_auto_corr_beta) > 15 and np.std(store_auto_corr_beta) != 0:
                    
                    # Enter an order if autocorrelation signal activates
                    if side == 'neutral' and (store_auto_corr_beta[-1] - np.mean(store_auto_corr_beta))/np.std(store_auto_corr_beta) < -2.33:
                        await self.XLimitBuy(session, "XBTUSD", self.khigh_bid, volume, cl_ord_ida)
                        side = 'long'
                        self.printer = f"Entered Long Position: {rightNow()}"
                        t0 = postage_stamp()
                        tv0 = postage_stamp() + self.exit_trade

                    del store_auto_corr_beta[0]

                else:
                    self.printer = f'Still need {15 - len(store_auto_corr_beta)} autocorrelations'

                if side == 'long':
                    diff = TrT(tv0 - postage_stamp())
                    self.gain_or_loss = self.klow_ask - self.entry_price
                    self.printer = f'Currently in a long position, time left in trade: {diff}'
                    

            await asyncio.sleep(0.001)

    # Outputs the data at high speeds to React.js
    async def ServerFeed(self, ws):
        self.current_balance = self.api.Balance()
        u0 = postage_stamp()
        while True:
            if self.Synchronize():
                msg = {'logger': self.printer,
                    'prices':[self.kprice, self.khigh_bid, self.klow_ask, round(self.cbook, 4), round(self.cbsd,4), round(self.gain_or_loss, 5)],
                    'book': self.obook_graph,
                    'profit': {'x':list(range(len(self.profit))), 'y': self.profit}}
 
                await ws.send(json.dumps(msg))
            
            await asyncio.sleep(0.001)
            
        

print("System Initialized")
trader = Trader()
trader.ignition()






