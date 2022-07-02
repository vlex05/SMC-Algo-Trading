from PySide2.QtWidgets import QGraphicsTextItem
from PySide2.QtGui import QBrush,QPen
from PySide2.QtCore import Qt

class Vertex():
    def __init__(self,x=None,y=None):
        self.x = x
        self.y = y
        self.type = None
        self.last = None
        self.next = None
        self.breaks = False
        self.is_first = False
        self.is_last = False
        self.protected_low = None
        self.protected_high = None

        self.is_choch = False
        self.is_cos = False

    def __repr__(self):
        out = []
        out.append(self.type)
        out.append(self.x)
        out.append(self.y)
        if self.is_cos:
            out.append("COS")
        if self.is_choch:
            out.append("CHOCH")
        return str(out)

    def draw(self,scene):
        x = self.x
        y = self.y

        txt = self.type
        # if self.is_choch:
        #     txt+= " + CHOCH"

        if self.type == "HH":
            text = QGraphicsTextItem(txt)
            text.setX(x)
            text.setY(y-25)
            font = text.font()
            font.setPointSize(12)
            font.setBold(True)
            pen = QPen(Qt.darkBlue)
            pen.setWidth(4)
            scene.addLine(x, y, x+20, y, pen)
            scene.addItem(text)

        elif self.type == "HL":
            text = QGraphicsTextItem(txt)
            text.setX(x)
            text.setY(y+5)
            font = text.font()
            font.setPointSize(12)
            font.setBold(True)
            pen = QPen(Qt.darkBlue)
            pen.setWidth(4)
            scene.addLine(x, y, x+20, y, pen)
            scene.addItem(text)

        elif self.type == "LL":
            text = QGraphicsTextItem(txt)
            text.setX(x)
            text.setY(y+5)
            font = text.font()
            font.setPointSize(12)
            font.setBold(True)
            pen = QPen(Qt.darkBlue)
            pen.setWidth(4)
            scene.addLine(x, y, x+20, y, pen)
            scene.addItem(text)


        elif self.type == "LH":
            text = QGraphicsTextItem(txt)
            text.setX(x)
            text.setY(y-25)
            font = text.font()
            font.setPointSize(12)
            font.setBold(True)
            pen = QPen(Qt.darkBlue)
            pen.setWidth(4)
            scene.addLine(x, y, x+20, y, pen)
            scene.addItem(text)

    def locate(self):
        print("------------------Vertex.locate() -----------------------")
        # ----------------------  check if first -----------------------
        if self.last is None:
            self.is_first = True
            print("is_first")
        else:
            self.is_first = False

        # ------------------------ check if last  ------------------------
        if self.next is None:
            self.is_last = True
            print("is_last")
        else:
            self.is_last = False

        # --------------------  check if high or  low -----------------------
        print("self: " + str(self))
        if self.is_first:

            print("next: " + str(self.next))
            if self.next is not None:
                if self.is_over(self.next):
                    print("self is over next")
                    self.type = "H"
                elif self.is_under(self.next):
                    print("self is under next")
                    self.type = "L"
                else:
                    self.type = "EQ"
        else:
            print("last: " + str(self.last))
            if self.is_over(self.last):
                print("self is over last")
                self.type = "H"
                print("self i H")
            elif self.is_under(self.last):
                print("self is under last")
                self.type = "L"
                print("self i L")
            else:
                self.type = "EQ"

        # ------------------ if first movement, define first protected H/L--------------------
        if self.is_first and self.is_H():
            self.protected_high = self
            self.protected_low = self.next

        elif self.is_first and self.is_L():
            self.protected_high = self.next
            self.protected_low = self

        elif self.last.is_first and self.is_H():
            self.protected_high = self
            self.protected_low = self.last

        elif self.last.is_first and self.is_H():
            self.protected_high = self.last
            self.protected_low = self

        # ------------------------  else check if this H/L break the last one -----------------

        else:

            # first define the protected high/low at the ones of this vertex

            self.protected_low = self.last.protected_low
            self.protected_high = self.last.protected_high

            # ------------------ if vertex is L --------------------------------

            if self.is_L:


                if self.is_under(self.protected_low):
                    self.breaks = True
                    self.type = "LL"
                    print("self is LL")
                    print(self.last.type)
                    if  self.last.type == "H":
                        print("last is LH")
                        self.last.type = 'LH'

                    self.protected_low = self
                    self.protected_high = self.last
                    self.last.protected_low = self
                    self.last.protected_high = self.last

                else:
                    self.protected_high = self.last.protected_high
                    self.protected_low = self.last.protected_low

                if self.breaks:

                    if self.last.protected_high.type == "HH":
                        self.is_choch = True
                        self.is_cos = False

                    elif self.last.protected_high.type == "LH":

                        self.is_choch = False
                        self.is_cos = True


            # ---------------------------------- if vertex is H --------------------

            if self.last.is_L:


                if self.is_over(self.protected_high):
                    self.breaks = True
                    self.type = "HH"
                    print("self is HH")
                    print(self.last.type)
                    if self.last.type == "L":
                        print("last is HL")
                        self.last.type = 'HL'
                    self.protected_low = self.last
                    self.protected_high = self
                    self.last.protected_low = self.last
                    self.last.protected_high = self

                else:
                    self.protected_high = self.last.protected_high
                    self.protected_low = self.last.protected_low

                if self.breaks:

                    if self.last.protected_high.type == "LL" :
                        self.is_choch = True
                        self.is_cos = False

                    elif self.last.protected_high.type == "HL":
                        self.is_choch = False
                        self.is_cos = True

    def is_HH(self):
        if self.type == "HH":
            return True
        else:
            return False

    def is_HL(self):
        if self.type == "HL":
            return True
        else:
            return False

    def is_LH(self):
        if self.type == "LH":
            return True
        else:
            return False

    def is_LL(self):
        if self.type == "LL":
            return True
        else:
            return False

    def is_H(self):
        if self.type == "LH" or self.type == 'HH' or self.type == 'H':
            return True
        else:
            return False

    def is_L(self):
        if self.type == "LL" or self.type == 'HL' or self.type == 'L':
            return True
        else:
            return False

    def set_next(self,n):
        self.next = n
        # self.trend()

    def set_last(self,l):
        self.last = l
        # self.trend()

    def break_by(self):
        return self.breaker

    def is_over(self,other):
        if self.y > other.y:
            return True
        else:
            return False

    def is_under(self, other):
        if self.y < other.y:
            return True
        else:
            return False
