
import os, time
from pathlib import Path
import sys
import math,datetime

import MetaTrader5 as mt5

from PySide2.QtWidgets import QApplication, QWidget, QGraphicsView, QGraphicsItem, QGraphicsScene, QDesktopWidget, QGraphicsTextItem
from PySide2.QtCore import QFile, QThread, QObject, Signal, Qt, QLineF, QPointF, QRect, QPoint
from PySide2.QtGui import QBrush,QPen
from PySide2.QtUiTools import QUiLoader

from PySide2.QtWebEngineWidgets import *

from Candle import Candle

from Vertex import Vertex



class DataLoop(QThread):
    signal = Signal()

    def __init__(self,display):
        super(DataLoop, self).__init__()
        self.symbol = display.symbol
        self.cd_data = []
        self.display = display
        self.candle_nb = display.candle_nb

    def __del__(self):
        self.wait()

    def run(self):

        while True:
            # print(datetime.datetime.now())
            # print("run")

            time.sleep(0.2)

            self.display.process_data(self.display.symbol)

            self.signal.emit()
            # print("end of loop")



class Display(QWidget):
    def __init__(self):
        super(Display, self).__init__()
        # self.setWindowTitle("AlgoCrypto")
        loader = QUiLoader()
        path = os.fspath(Path(__file__).resolve().parent / "display.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        self.candle_data = []
        self.charts = []
        self.skeleton = []
        self.vertices = []

        self.cd_data = []
        self.chart_data = []

        mt5.initialize()

        self.symbol = "BTCUSD"

        self.candle_nb = 150
        self.smooth_y = 50

        self.tf = mt5.TIMEFRAME_M1

        # self.ui.slider.setValue = self.smooth_y
        self.ui.slider_2.setValue = self.candle_nb

        self.build_scene()
        self.process_data(self.symbol)
        self.update_scene()

        self.move(30, 30)

        self.thread = DataLoop(self)
        self.thread.signal.connect(self.update_scene)

        self.ui.b_m1.clicked.connect(self.on_b_m1)
        self.ui.b_m3.clicked.connect(self.on_b_m3)
        self.ui.b_m5.clicked.connect(self.on_b_m5)
        self.ui.b_m15.clicked.connect(self.on_b_m15)
        self.ui.b_h1.clicked.connect(self.on_b_h1)
        self.ui.b_h4.clicked.connect(self.on_b_h4)
        self.ui.b_d1.clicked.connect(self.on_b_d1)
        self.ui.b_w1.clicked.connect(self.on_b_w1)
        self.ui.b_mn1.clicked.connect(self.on_b_mn1)

        self.show()
        self.thread.start()

    def test(self):
        print("test")

    def process_data(self,symbol):



        data = self.get_candles(symbol, self.candle_nb)

        self.cd_data = data

    def to_candle(self,data):

        candles = []

        for i in data:
            a = Candle(None)
            a.date = i[0]
            a.O = i[1]
            a.H = i[2]
            a.L = i[3]
            a.C = i[4]
            a.trend()
            candles.append(a)

        return candles

    def get_candles(self, symbol, nb):
        # print("get_candles")
        # print(self.tf)
        candle_list = mt5.copy_rates_from_pos(symbol, self.tf, 0, nb)
        candle_list = self.to_candle(candle_list)

        return candle_list

    def to_skeleton(self,data):

        # ------------------------------- build the trend blocks ------------------------------

        block_list = []
        block = []
        last = data[0]
        block.append(last)
        for i in range(1,len(data)):
            actual = data[i]
            if last.trend() != actual.trend():
                block_list.append(block)
                block = []

            block.append(actual)
            last = actual

        # ---------------------------------if only one candle 'double' it  ------------------------

        for i in block_list:
            if len(i)< 2:
                a = Candle(None)
                a.O = i[0].O
                a.H = i[0].H
                a.L = i[0].L
                a.C = i[0].C
                a.date = i[0].date
                i.append(a)

        # # ------------------------------ find better top and bottom candle ----------------------


        for block in block_list:

            if block[-1].trend() == "bull":
                if block[-2].H > block[-1].H:
                    block.pop(-1)

            elif block[-1].trend() == "bear":
                if block[-2].L < block[-1].L:
                    block.pop(-1)


        # ------------------------ join the edges ------------------------

        for i in range(1,len(block_list)):
            last = block_list[i-1][-1]
            actual = block_list[i][0]

            if last.trend() == "bull":
                if last.H < actual.H:
                    top = actual.H
                    date = actual.date
                else:
                    top = last.H
                    date = last.date

                block_list[i-1][-1].H = top
                block_list[i-1][-1].date = date
                block_list[i][0].H = top
                block_list[i][0].date = date

            else:
                if last.L > actual.L:
                    low = actual.L
                    date = actual.date
                else:
                    low = last.L
                    date = last.date

                block_list[i-1][-1].L = low
                block_list[i-1][-1].date = date
                block_list[i][0].L = low
                block_list[i][0].date = date

                # ------------------------------- display blocks ------------------------------
        # i = 0
        # for a in block_list:
        #     print("-------------Block " + str(i) + " ---------------")
        #     i += 1
        #     for b in a:
        #         print(b)
        #
        #     print("   ")
        #
        # print("------------------+++++++++++++++++++++-------------------------")



        # for i in simple_blocks:
        #     print(i)

        # ----------------------- simplify the block, only keep first and last candle --------------

        simple_block = []

        for i in block_list:
            simple_block.append([i[0],i[-1]])


        # for i in simple_block:
        #     print(i)

        return simple_block

    def build_skeleton(self):

        # print("build skeleton")

        # ------------------- convert candle to skeleton ------------

        data = self.to_skeleton(self.cd_data)

        # for i in data:
        #     print(i)

        # ------------------------convert candle to lines -------------------

        polyline = []

        for i in data:

            if i[0].trend() == "bull":
                # point_A = QPointF(i[0].date, self.y(i[0].L))
                # point_B = QPointF(i[1].date, self.y(i[1].H))
                point_A = QPointF(i[0].date, i[0].L)
                point_B = QPointF(i[1].date, i[1].H)
            else:
                # point_A = QPointF(i[0].date, self.y(i[0].H))
                # point_B = QPointF(i[1].date, self.y(i[1].L))
                point_A = QPointF(i[0].date, i[0].H)
                point_B = QPointF(i[1].date, i[1].L)

            polyline.append([point_A, point_B])

        # print("------------------------- polyline ------------------------------")
        #
        # for i in polyline:
        #     print(i)

        # print(" ------------------ ")
        #
        # print(len(polyline))

        polyline = self.smooth(polyline)

        self.skeleton = polyline
        #
        # for i in polyline:
        #     print(i)

        self.build_vertices()

        for i in polyline:

            i[0].setY(self.y(i[0].y()))
            i[1].setY(self.y(i[1].y()))

        # print(" +++++++++++++++++++ ")
        #
        # for i in polyline:
        #     print(i)

        self.skeleton = polyline

    def build_vertices(self):
        print(" -----------------------  build vertices  -------------------------------")

        print(self.skeleton)

        if len(self.skeleton)>1:

            self.vertices = []

            skeleton = self.skeleton

            first = Vertex(skeleton[0][0].x(), skeleton[0][0].y())
            first.is_first = True
            self.vertices.append(first)
            for i in skeleton:
                next = Vertex(i[1].x(), i[1].y())
                last = self.vertices[-1]
                last.set_next(next)
                next.set_last(last)
                self.vertices.append(next)
            print("-----------------------------------------------------------")
            print("-----------------------------------------------------------")
            print("-----------------------------------------------------------")
            print(self.vertices)
            print("+++")

            for i in self.vertices:
                i.locate()

            print(self.vertices)

    def trend(self,line):

        if line[0].y() < line[1].y():
            return "bull"
        else:
            return "bear"

    def smooth(self,polyline):
        # print("-------------------------------- smooth --------------------------------")

        # print("before clean")
        # a = []
        # for i in polyline:
        #     delta = abs(i[0].y() - i[1].y())
        #     a.append(delta)
        #
        # print(a)

        a =1
        while a < len(polyline)-1:
            i = polyline[a]
            delta = abs(i[0].y() - i[1].y())
            if delta == 0:
                polyline.pop(a)
            a += 1

        # print("before smooth")
        # a = []
        # for i in polyline:
        #     delta = abs(i[0].y() - i[1].y())
        #     a.append(delta)
        #
        # print(a)

        # print("-----     -----")

        # print(len(polyline))

        linear_smooth = self.ui.slider.value()

        # smooth_y = (linear_smooth * linear_smooth)
        smooth_y = linear_smooth

        self.ui.smooth.setText(str(smooth_y))

        # print("--smooth--" + str(smooth_y))
        while len(polyline) > 2:
            # print("while " + str(len(polyline)))

            smallest = 0
            i_smallest = 0

            # find smallest element
            for i in range(1,len(polyline)-1):
                line = polyline[i]
                delta = abs(line[0].y()-line[1].y())
                if smallest == 0 or delta < smallest:
                    smallest = delta
                    i_smallest = i

            # print("position " + str(i_smallest) + ":" + str(smallest))

            line = polyline[i_smallest]
            delta = abs(line[0].y() - line[1].y())

            print()

            if abs(delta) < smooth_y:
                # print("delete ["  + str(i_smallest) + "] : " + str( abs(delta)))
                last = polyline[i_smallest-1]
                next = polyline[i_smallest+1]
                last[1] = next[1]
                polyline.pop(i_smallest)
                polyline.pop(i_smallest)
            else:
                break

        # print("after smooth")
        # print(len(polyline))


        # a = []
        # for i in polyline:
        #     delta = abs(i[0].y() - i[1].y())
        #     a.append(delta)
        #
        # print(a)



        #  ----------------merge if double bullish or double bearish ------------------

        i = 1
        while i < len(polyline)-1:
            # print("while")

            last = polyline[i-1]
            actual = polyline[i]

            last_delta = last[1].y()-last[0].y()
            actual_delta = actual[1].y() - actual[0].y()
            # print(last_delta)
            # print(actual_delta)

            if (last_delta > 0 and actual_delta > 0) or (last_delta < 0 and actual_delta < 0): # if both bullish
                last[1].setY(actual[1].y())
                last[1].setX(actual[1].x())
                polyline.pop(i)
            else:
                i += 1



        # ---------------- fix the gap -------------------

        i = 1
        while i < len(polyline) - 1:

            last = polyline[i - 1]
            actual = polyline[i]

            gap = last[1].x() - actual[0].x()
            last_delta = last[1].x() - last[0].x()
            actual_delta = actual[1].x() - actual[0].x()

            if abs(gap) > 0:
                if actual_delta == 0:
                    actual[0].setX(last[1].x())
                else:
                    last[1].setX(actual[0].x())

            else:
                i += 1



        # for i in polyline:
        #     print(i)
        #
        # print("--------------------------------smooth  end --------------------------------")

        return polyline

    def build_scene(self):

        self.scene = QGraphicsScene()
        self.black = QBrush(Qt.white)
        self.pen = QPen(Qt.white)
        self.pen.setWidth(2)

        self.ui.graphicsView.setScene(self.scene)

    def update_scene(self):
        # print("display.update_scene")

        self.candle_nb = self.ui.slider_2.value()

        minmax = self.cd_data
        list_min = []
        list_max = []

        for i in minmax:
            list_min.append(i.L)
            list_max.append(i.H)

        i = 0

        _min = min(list_min)
        _max = max(list_max)

        self.scene.clear()
        self.scene_w = self.ui.graphicsView.width()
        self.scene_h = self.ui.graphicsView.height()

        self.scene_max = _max *1.01
        self.scene_min = _min *0.99

        print(_min)
        print(_max)

        background_color = Qt.darkGray
        self.scene_background = QBrush(background_color)
        self.scene_background_pen = QPen(background_color)
        self.ui.graphicsView.setBackgroundBrush(self.scene_background)

        self.green_brush = QBrush(Qt.green)
        self.green_pen = QPen(Qt.green)

        self.red_brush = QBrush(Qt.red)
        self.red_pen = QPen(Qt.red)


        self.right_border = 0.1
        self.right_border *= self.scene_w
        self.right_border = round(self.right_border)


        self.display_width = self.scene_w - self.right_border

        self.candle_step = round(self.display_width / (self.candle_nb + 1))
        self.candle_w = round(self.candle_step*0.8)


        self.update_candle()

    def update_candle(self):

        self.select_candle()

        for i in self.cd_data:
            self.add_candle(i)

        self.build_skeleton()

        pen = QPen(Qt.lightGray)
        pen.setWidth(4)

        for i in self.skeleton:
            self.scene.addLine(i[0].x(),i[0].y(),i[1].x(),i[1].y(),pen)

        for i in self.vertices:
            i.y = self.y(i.y)

        for i in self.vertices:
            i.draw(self.scene)

    def select_candle(self):
        strt = len(self.cd_data) - self.candle_nb

        data = self.cd_data[strt:]

        new_data = []

        for i in range(len(data)):
            cd = data[i]

            x = (i * self.candle_step)

            cd.date = x
            new_data.append(cd)

        self.cd_data = new_data

    def update_chart(self):
       pass

    def y(self,_y):
        y =  self.scene_h - round(((_y - self.scene_min) /(self.scene_max - self.scene_min) * self.scene_h))

        return y

    def add_candle(self,_candle):

        if _candle.C < _candle.O:
            pen = self.red_pen
            brush = self.red_brush
        else:
            pen = self.green_pen
            brush = self.green_brush


        open = self.y(_candle.O)
        close = self.y(_candle.C)
        high = self.y(_candle.H)
        low = self.y(_candle.L)

        x = _candle.date

        x1 = x - (self.candle_w/2)
        x2 = x + (self.candle_w/2)

        candle = QRect(QPoint(x1,open),QPoint(x2,close))
        self.scene.addLine(x,high,x,low,pen)
        self.scene.addRect(candle,pen,brush)
        pass

    def on_b_m1(self):
        self.tf = mt5.TIMEFRAME_M1

    def on_b_m3(self):

        self.tf = mt5.TIMEFRAME_M3

    def on_b_m5(self):
        self.tf = mt5.TIMEFRAME_M5

    def on_b_m15(self):
        self.tf = mt5.TIMEFRAME_M15

    def on_b_h1(self):
        self.tf = mt5.TIMEFRAME_H1

    def on_b_h4(self):
        self.tf = mt5.TIMEFRAME_H4

    def on_b_d1(self):
        self.tf = mt5.TIMEFRAME_D1

    def on_b_w1(self):
        self.tf = mt5.TIMEFRAME_W1

    def on_b_mn1(self):
        self.tf = mt5.TIMEFRAME_MN1



if __name__ == "__main__":
    app = QApplication([])
    widget = Display()

    widget.showMaximized()

    sys.exit(app.exec_())