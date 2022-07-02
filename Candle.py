
class Candle():

    def __init__(self,data):
        if data is not None:
            self.O = data["open"]
            self.H = data["high"]
            self.L = data["low"]
            self.C = data["close"]
            self.date = data["date"]
            try:
                self.dnert = data["trend"]
            except:
                self.dnert = None
                pass
            self.trend()

        else:
            self.O = None
            self.H = None
            self.L = None
            self.C = None
            self.date = None
            self.dnert = None

    def __repr__(self):
        a = [self.O,self.H,self.L,self.C,self.date,self.dnert]
        b = str(a)
        return b

    def trend(self):
        if self.O is None or self.C is None:
            return self.dnert()

        elif self.O > self.C:
            self.dnert = "bear"
            return self.dnert
        elif self.O < self.C:
            self.dnert = "bull"
            return self.dnert
        else:
            return None
