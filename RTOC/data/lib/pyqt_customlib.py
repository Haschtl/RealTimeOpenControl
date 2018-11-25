# -*- encoding: utf-8 -*-
import time
import datetime
import traceback
import markdown2

import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5 import QtWidgets, QtGui, Qt
from PyQt5 import uic
from functools import partial

from . import general_lib as lib

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

define = ""

def remRow(self, row):
    self.gridlayout.removeWidget(self.entries[row])
    self.entries[row].deleteLater()
    del self.entries[row]

def markElement(QElement):
    QElement.setStyleSheet("border: 3px solid #d00808;")

def unmarkElement(QElement):
    QElement.setStyleSheet("")

class QHLine(QtWidgets.QFrame):
    def __init__(self, width=2):
        super(QHLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.setLineWidth(width)
        self.setStyleSheet("color: black; background-color: black;")


class QVLine(QtWidgets.QFrame):
    def __init__(self, width=2):
        super(QVLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.VLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.setLineWidth(width)
        self.setStyleSheet("color: black; background-color: black;")

def getListWidgets(QListWidget):
    items = []
    for x in range(QListWidget.count()):
        items.append(QListWidget.itemWidget(QListWidget.item(x)))#,QListWidget.item(x)])
    return items


# Message Functions

class date_message(QtWidgets.QDialog):

    def __init__(self, date=[0, 0, 0, 0, 0, 0], stylesheet=""):
        super(date_message, self).__init__()
        uic.loadUi(define.ui_path+"date_message.ui", self)
        self.setStyleSheet(stylesheet)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        x = (QtWidgets.QDesktopWidget().availableGeometry().width()-self.frameGeometry().width())/2+180
        y = (QtWidgets.QDesktopWidget().availableGeometry().height()-self.frameGeometry().height())/2+100
        if date == [0, 0, 0, 0, 0, 0]:
            now = datetime.datetime.now()
            date = [now.year, now.month, now.day, now.hour, now.minute, now.second]
        self.calendarWidget.setSelectedDate(QtCore.QDate(date[0], date[1], date[2]))
        self.timeEdit.setTime(QtCore.QTime(date[3], date[4], date[5]))
        self.move(x, y)
        self.status = "abort"

        self.abort_button.clicked.connect(self.abort)
        self.delete_button.clicked.connect(self.delete)
        self.add_button.clicked.connect(self.save)
        self.exec_()

    def abort(self):
        self.status = "abort"
        self.close()

    def delete(self):
        self.status = "delete"
        self.close()

    def save(self):
        self.status = "save"
        self.close()

    def closeEvent(self, *args, **kwargs):
        if self.status == "abort":
            self.answer = "abort"
        elif self.status == "delete":
            self.answer = "delete"
        else:
            date=self.calendarWidget.selectedDate()
            time=self.timeEdit.time()
            self.answer = [date.year(), date.month(), date.day(), time.hour(), time.minute(), time.second()]

def alert_message(title, text, info, stylesheet="", okbutton="OK", cancelbutton="Abbrechen"):
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Warning)

    msg.setText(text)
    msg.setInformativeText(info)
    msg.setWindowTitle(title)
    msg.addButton(okbutton, QtWidgets.QMessageBox.YesRole)
    msg.addButton(cancelbutton, QtWidgets.QMessageBox.NoRole)
    msg.setStyleSheet(stylesheet)
    msg.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
    # x = (QtWidgets.QDesktopWidget().availableGeometry().width()-msg.frameGeometry().width())/2+180
    # y = (QtWidgets.QDesktopWidget().availableGeometry().height()-msg.frameGeometry().height())/2+100
    # msg.move(x, y)
    retval = msg.exec_()
    if retval is 0:
        return True
    else:
        return False

def tri_message(title, text, info, stylesheet="", okbutton="Ja", nobutton="Nein",cancelbutton="Abbrechen"):
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Warning)

    msg.setText(text)
    msg.setInformativeText(info)
    msg.setWindowTitle(title)
    msg.addButton(okbutton, QtWidgets.QMessageBox.YesRole)
    msg.addButton(nobutton, QtWidgets.QMessageBox.NoRole)
    msg.addButton(cancelbutton, QtWidgets.QMessageBox.NoRole)
    msg.setStyleSheet(stylesheet)
    msg.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
    #x = (QtWidgets.QDesktopWidget().availableGeometry().width()-msg.frameGeometry().width())/2+180
    #y = (QtWidgets.QDesktopWidget().availableGeometry().height()-msg.frameGeometry().height())/2+100
    #msg.move(x, y)
    retval = msg.exec_()
    if retval is 0:
        return True
    elif retval is 1:
        return False
    else:
        return None

def info_message(title, text, info, stylesheet=""):
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Information)

    msg.setText(text)
    msg.setInformativeText(info)
    msg.setWindowTitle(title)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.setStyleSheet(stylesheet)
    msg.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
    # x = (QtWidgets.QDesktopWidget().availableGeometry().width()-msg.frameGeometry().width())/2+180
    # y = (QtWidgets.QDesktopWidget().availableGeometry().height()-msg.frameGeometry().height())/2+100
    # msg.move(x, y)
    retval = msg.exec_()
    return retval


def item_message(self, title, text, items, stylesheet=""):

    item, ok = QtWidgets.QInputDialog.getItem(self, title,
                                              text, items, 0, False)
    return item, ok


def text_message(self, title, text, placeholdertext, stylesheet=""):
    text, ok = QtWidgets.QInputDialog.getText(
        self, title, text, QtWidgets.QLineEdit.Normal, placeholdertext)

    return text, ok


def int_message(self, title, text, stylesheet=""):
    num, ok = QtWidgets.QInputDialog.getInt(self, title, text)

    return num, ok


# Icon functions

def set_hoverIcon(QElement, QType, iconname, iconsize=0):
    if iconsize is not 0:
        iconsize = 'size: '+str(iconsize)+'px '+str(iconsize)+'px'
    else:
        iconsize = ''
    stylesheet = QType+":hover { image: url(ui/icons/"+iconname+"); "+iconsize+"}"
    QElement.setStyleSheet(stylesheet)


def set_Icon(QElement, iconname, QType='QPushButton', filetype='png'):
    if define.bigicons:
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(define.ui_path+"icons/"+iconname +
                                               "."+filetype)), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        QElement.setIcon(icon)
    else:
        stylesheet = QType+" { image: url("+define.ui_path+"icons/"+iconname+"."+filetype+");}"
    stylesheet = stylesheet+QType + \
        ":hover { image: url("+define.ui_path+"icons/"+iconname+"_hovered."+filetype+");}"
    QElement.setStyleSheet(stylesheet)


def set_Icon_all(QElement, icon_pressed, icon_unpressed):
    icon = QtGui.QIcon()
    icon.addFile("ui/icons/"+icon_unpressed, QtCore.QSize(), QtGui.QIcon.Normal, QtGui.QIcon.Off)
    icon.addFile("ui/icons/"+icon_pressed, QtCore.QSize(), QtGui.QIcon.Active, QtGui.QIcon.Off)
    icon.addFile("ui/icons/"+icon_unpressed, QtCore.QSize(), QtGui.QIcon.Normal, QtGui.QIcon.On)
    icon.addFile("ui/icons/"+icon_pressed, QtCore.QSize(), QtGui.QIcon.Active, QtGui.QIcon.On)
    QElement.setIcon(icon)


def set_clickedIcon(self, QElement, QType, iconname):
    stylesheet = QType+":checked, "+QType+":pressed { image: url(ui/icons/"+iconname+");}"
    QElement.setStyleSheet(stylesheet)



def clearLayout(layout):
    while layout.count():
        child = layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()


def setHorScaleCursor():
    Qt.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.SizeHorCursor))


def setVerScaleCursor():
    Qt.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.SizeVerCursor))


def restoreCursor():
    Qt.QApplication.restoreOverrideCursor()


class GrowingQListWidget(QtWidgets.QListWidget):
    def __init__(self, *args, **kwargs):
        super(GrowingQListWidget, self).__init__(*args, **kwargs)
        #self.document().contentsChanged.connect(self.sizeChange)
        self.heightMin = 40
        self.heightMax = 2000
        self.setAlternatingRowColors(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setFrameShadow(QtWidgets.QFrame.Plain)
        self.setLineWidth(0)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)


    def setHeight(self,item, contentEdit):
        #print("This is called, when content changes")
        #self.updateGeometry()
        size=contentEdit.document().size().height() + contentEdit.contentsMargins().top()+contentEdit.contentsMargins().bottom()
        if self.heightMin <= size <= self.heightMax:
            s=QtCore.QSize()
            s.setHeight(size)
            item.setSizeHint(s)
            #contentEdit.sizeChange()
        if size<self.heightMin:
            s=QtCore.QSize()
            s.setHeight(self.heightMin)
            item.setSizeHint(s)
        if size>self.heightMax:
            s=QtCore.QSize()
            s.setHeight(self.heightMax)
            item.setSizeHint(s)

    def setItemWidget2(self, item, element):
        self.setItemWidget(item, element)
        element.contentEdit.document().contentsChanged.connect(partial(self.setHeight,item, element.contentEdit))
        element.contentEdit.sizeChange()
        self.setHeight(item, element.contentEdit)

    def sizeHint(self):
        s = QtCore.QSize()
        s.setHeight(super(GrowingQListWidget,self).sizeHint().height())
        s.setWidth(self.sizeHintForColumn(0))
        return s

class GrowingQListWidgetItem(QtWidgets.QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super(GrowingQListWidgetItem, self).__init__(*args, **kwargs)
        #self.document().contentsChanged.connect(self.sizeChange)
        self.heightMin = 0
        self.heightMax = 10
        #self.setSizeHint(QtCore.QSize(1000,1000).expandedTo(QtCore.QSize(100,100)))
        #print(self.sizeHint())

        # self.sizeChange()
        #self.setFontPointSize(10)
        #self.setFont(QtGui.QFont('SansSerif', 10))
        #self.setFixedHeight(40)


class GrowingTextEdit(QtWidgets.QTextEdit):
    returnPressed = QtCore.pyqtSignal(str)
    #clicked2 = QtCore.pyqtSignal() # signal when the text entry is left clicked

    def __init__(self, *args, **kwargs):
        super(GrowingTextEdit, self).__init__(*args, **kwargs)
        self.document().contentsChanged.connect(self.sizeChange)

        self.heightMin = 40
        self.heightMax = 2000
        # self.sizeChange()
        self.setFontPointSize(10)
        self.setFont(QtGui.QFont('SansSerif', 10))
        # self.setAttribute(103)
        self.setFixedHeight(40)
        # self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # self.setMinimumHeight(28)
        self.completer = None
        # self.returnPressed.emit(self.enterEvent())
        #self.clicked2.connect(self.showPlainText)
        self.placeholderText=""

    def sizeChange(self):
        # docHeight = self.document().size().height()
        # nlines = self.text().count('\n')
        # if nlines is 0:
        #     nlines = 1
        size=self.document().size().height() + self.contentsMargins().top()+self.contentsMargins().bottom()
        if self.heightMin <= size <= self.heightMax:
            #self.setFixedHeight((nlines-1)*34+40)
            self.setFixedHeight(size)
            # self.setFixedHeight(docHeight)
        if size<self.heightMin:
            self.setFixedHeight(self.heightMin)
        if size>self.heightMax:
            self.setFixedHeight(self.heightMax)

    #def mousePressEvent(self, event):
    #    if event.button() == QtCore.Qt.LeftButton: self.clicked.emit()
    #    else: super().mousePressEvent(event)

    def text(self):
        return self.toPlainText()
        #return self.originalText

    #def showPlainText(self):
    #    self.setText(self.originalText)

    def setText2(self, text):
        #self.originalText=text
        self.setText(text)
        #self.setPlainText(markdown2.markdown(text))
        # docHeight = self.document().size().height()
        self.sizeChange()
        # self.setFixedHeight(40+(nlines-1)*25)

    #def setPlaceholderText(self, text):
    #    self.placeholderText = text

    def paintEvent(self, _event):
        """
        Implements the same behavior as QLineEdit's setPlaceholderText()
        Draw the placeholder text when there is no text entered and the widget
        doesn't have focus.
        """
        if self.placeholderText and not self.hasFocus() and not self.toPlainText():
            painter = QtGui.QPainter(self.viewport())

            color = self.palette().text().color()
            color.setAlpha(128)
            painter.setPen(color)

            painter.drawText(self.geometry().topLeft(), self.placeholderText)

        else:
            super(GrowingTextEdit, self).paintEvent(_event)

    def setCompleter(self, completer):
        if self.completer:
            #self.disconnect(self.completer, 0, self, 0)
            pass
        if not completer:
            return

        completer.setWidget(self)
        completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.completer = completer
        self.completer.insertText.connect(self.insertCompletion)

    def insertCompletion(self, completion):
        tc = self.textCursor()
        extra = (len(completion) - len(self.completer.completionPrefix()))
        tc.movePosition(QtGui.QTextCursor.Left)
        tc.movePosition(QtGui.QTextCursor.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)
        self.completer.popup().hide()

    def focusInEvent(self, event):
        if self.completer:
            self.completer.setWidget(self)
        QtWidgets.QTextEdit.focusInEvent(self, event)

    def returnPressed(self, text):
        lib.logging("ENTER")
        lib.logging(text)
        pass

    # def keyPressEvent(self, event):
    #
    #     tc = self.textCursor()
    #     if event.key() is QtCore.Qt.Key_Tab and self.completer.popup().isVisible():
    #         self.completer.insertText.emit(self.completer.getSelected())
    #         self.completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
    #         return
    #
    #     QtWidgets.QTextEdit.keyPressEvent(self, event)
    #     tc.select(QtGui.QTextCursor.WordUnderCursor)
    #     cr = self.cursorRect()
    #
    #     if len(tc.selectedText()) > 0:
    #         self.completer.setCompletionPrefix(tc.selectedText())
    #         popup = self.completer.popup()
    #         popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
    #
    #         cr.setWidth(self.completer.popup().sizeHintForColumn(0)
    #                     + self.completer.popup().verticalScrollBar().sizeHint().width())
    #         self.completer.complete(cr)
    #     else:
    #         self.completer.popup().hide()


class MyCompleter(QtWidgets.QCompleter):
    # source: https://stackoverflow.com/questions/28956693/pyqt5-qtextedit-auto-completion
    insertText = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        QtWidgets.QCompleter.__init__(self, ["test", "foo", "bar"], parent)
        self.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.highlighted.connect(self.setHighlighted)

    def setHighlighted(self, text):
        self.lastSelected = text

    def getSelected(self):
        return self.lastSelected


class scriptsWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self)

        self.name = ''

        self.widget_QHBoxLayout = QtWidgets.QHBoxLayout(self)
        self.widget_QHBoxLayout.setSpacing(0)
        self.widget_QHBoxLayout.setContentsMargins(0, 0, 0, 0)

        self.name_QLabel = QtWidgets.QLabel(self)
        self.widget_QHBoxLayout.addWidget(self.name_QLabel)

        self.user_QLabel = QtWidgets.QLabel(self)
        self.widget_QHBoxLayout.addWidget(self.user_QLabel)

        self.widget_QHBoxLayout.setSpacing(0)
        self.widget_QHBoxLayout.setContentsMargins(0, 0, 0, 0)

    def setName(self, name):
        self.name_QLabel.setText(name)
        self.name = name

    def setUser(self, user):
        self.user_QLabel.setText(user)


class customQListWidgetItem(QtWidgets.QListWidgetItem):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self)
        self.name = ''

    def setName(self, name):
        self.name = name


class DragDropListWidget(QtWidgets.QListWidget):
    # source: https://stackoverflow.com/questions/40142925/how-to-get-the-item-created-from-dropevent-on-a-qlistwidget
    _drag_info = []

    def __init__(self, parent=None):

        super(DragDropListWidget, self).__init__(parent)
        self.heightMin = 0
        self.heightMax = 65000
        self.counter = 0

        self.name = ''

    def sizeChange(self):
        docHeight = self.counter
        if self.heightMin <= docHeight <= self.heightMax:
            self.setFixedHeight(docHeight*22)

    def addItem2(self, item):
        self.addItem(item)
        self.counter = self.counter+1
        self.sizeChange()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()

        else:
            super(DragDropListWidget, self).dragMoveEvent(event)

    def dropEvent(self, event):
        lib.logging('dropEvent')
        lib.logging(event.mimeData().text())

        if event.mimeData().hasText():
            lib.logging(event.mimeData().text())
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            self.emit(QtCore.SIGNAL("dropped"), links)

        else:
            event.setDropAction(QtCore.Qt.CopyAction)
            super(DragDropListWidget, self).dropEvent(event)
            items = []
            for index in range(self.count()):  # was xrange() before
                items.append(self.item(index))
                lib.logging(self.item(index).data(QtCore.Qt.UserRole).toPyObject())

    def populate(self, items=[]):
        self.clear()
        for i in items:
            lib.logging(i)
            widget = scriptsWidget()
            widget.setName(i)
            widget.setUser('x')
            item = customQListWidgetItem()
            item.setName(i)
            data = (i)
            item.setData(QtCore.Qt.UserRole, data)
            self.addItem(item)
            self.setItemWidget(item, widget)


class PictureView(QtWidgets.QWidget):  # QtWidgets.QMainWindow):#

    def __init__(self, picturepath):
        super(PictureView, self).__init__()
        uic.loadUi(define.ui_path+"picture_view.ui", self)
        self.title = 'Bild'
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.setWindowTitle(self.title)
        # self.setGeometry(self.left, self.top, self.width, self.height)
        # Create widget
        pixmap = QtGui.QPixmap(picturepath)
        # pixmap.load(picturepath)
        self.label.setPixmap(pixmap)
        # self.layout=QtWidgets.QHBoxLayout()
        # self.main_widget.setLayout(self.main_layout)
        # self.layout.addWidget(self.label)
        # self.setLayout(self.layout)
        # self.resize(pixmap.width(),pixmap.height())
        # self.show()
        self.resize(pixmap.width(), pixmap.height())


class CustomQMainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(CustomQMainWindow, self).__init__(*args, **kwargs)
        lib.logging('Experimental WindowFrame')
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setMouseTracking(True)
        self.setBackgroundRole(QtGui.QPalette.Highlight)
        self.setAutoFillBackground(True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

    def dragEnterEvent(self, e):
        e.accept()

    def dragMoveEvent(self, e):
        e.accept()

    def mousePressEvent(self, event):
        self.offset = event.pos()
        self.oldsize = self.size()

    def mouseDoubleClickEvent(self, event):
        self.toggleFullscreen()

    def mouseHoverEvent(self, event):
        try:
            if self.isMaximized() is False:
                self.offset = event.pos()
                self.oldsize = self.size()
                # x = event.globalX()
                # y = event.globalY()
                x_w_offset = self.offset.x()
                y_w_offset = self.offset.y()
                if self.oldsize.width() - x_w_offset < 10 and self.oldsize.height() - y_w_offset < 10:
                    pass
                elif self.oldsize.width() - x_w_offset < 10:
                    setHorScaleCursor()
                elif self.oldsize.height() - y_w_offset < 10:
                    setVerScaleCursor()
                else:
                    restoreCursor()
        except:
            tb = traceback.format_exc()
            lib.logging(tb)

    def leaveEvent(self, event):
        restoreCursor()

    def mouseReleaseEvent(self, event):
        restoreCursor()
        if event.globalY() < 10:
            # self.showMaximized()
            # self.maximizeButton.hide()
            # self.demaximizeButton.show()
            self.toggleFullscreen()

    def mouseMoveEvent(self, event):
        try:
            if self.isMaximized() is False:
                x = event.globalX()
                y = event.globalY()
                x_w_offset = self.offset.x()
                y_w_offset = self.offset.y()
                if self.oldsize.width() - x_w_offset < 10 and self.oldsize.height() - y_w_offset < 10:
                    y_w_pos = self.geometry().top()
                    x_w_pos = self.geometry().left()
                    self.resize(self.oldsize.width()+x - x_w_pos, self.oldsize.height()+y - y_w_pos)
                elif self.oldsize.width() - x_w_offset < 10:
                    x_w_pos = self.geometry().left()
                    self.resize(x - x_w_pos, self.oldsize.height())
                elif self.oldsize.height() - y_w_offset < 10:
                    y_w_pos = self.geometry().top()
                    self.resize(self.oldsize.width(), y - y_w_pos)
                else:
                    self.move(x - x_w_offset, y - y_w_offset-1)
            else:
                self.toggleFullscreen()
        except:
            tb = traceback.format_exc()
            lib.logging(tb)

    def resizeEvent(self, event):
        pixmap = QtGui.QPixmap(self.size())
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setBrush(QtCore.Qt.black)
        painter.drawRoundedRect(pixmap.rect(), 8, 8)
        painter.end()
        self.setMask(pixmap.mask())


def timestamp():
    return int(time.mktime(datetime.datetime.now().timetuple()))


class TimeAxisItem(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLabel(text='Time', units=None)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        #return [datetime.datetime.fromtimestamp(value).strftime("%H:%M") for value in values]
        list = []
        for value in values:
            if value<0:
                sign = "-"
            else:
                sign = ""
            #if abs(value)<60:
            #    list.append(time.strftime("%S", time.gmtime(abs(value))))
            if abs(value)<60*60:

                list.append(sign+self.formatTime(value))
            elif abs(value)<60*60*24:
                list.append(sign+self.formatTime(value, "%H:%M:%S"))
            elif abs(value)<60*60*24*31:
                list.append(sign+time.strftime("%dT %H:%M", time.gmtime(abs(value))))
            else:
                list.append(sign+time.strftime("%mM %dT", time.gmtime(abs(value))))
        #return [time.strftime("%H:%M:%S", time.gmtime(int(value))) for value in values]
        return list
    def formatTime(self, value, format="%M:%S"):
        if int(value) == value:
            return time.strftime(format, time.gmtime(abs(value)))
        else:
            a = time.strftime(format, time.gmtime(abs(value)))
            a = a + " " + str(int(value%1*1000))+"ms"
            return a
    def attachToPlotItem(self, plotItem):
        """Add this axis to the given PlotItem
        :param plotItem: (PlotItem)
        """
        self.setParentItem(plotItem)
        viewBox = plotItem.getViewBox()
        self.linkToView(viewBox)
        self._oldAxis = plotItem.axes[self.orientation]['item']
        self._oldAxis.hide()
        #self._oldAxis.setParent(None)
        #self._oldAxis.deleteLater()
        plotItem.axes[self.orientation]['item'] = self
        pos = plotItem.axes[self.orientation]['pos']
        item = plotItem.layout.removeItem(self._oldAxis)
        #item.removeWidget(self._oldAxis)
        plotItem.layout.addItem(self, *pos)
        self.setZValue(-1000)
