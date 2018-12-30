#!/usr/bin/python3
#-*- coding:utf-8 -*-

# Source: https://python-forum.io/Thread-Read-Write-CSV-Qt5
# Functions to add:
# check if lengths are ok
# add change x,y
# add names
# x,y auswählen
# in signale konvertieren

import csv, codecs
import os

from PyQt5 import QtCore, QtGui, QtWidgets, QtPrintSupport
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtCore import QFile

class MyWindow(QtWidgets.QWidget):
   def __init__(self, fileName='', parent=None):
       super(MyWindow, self).__init__(parent)
       self.fileName = ""
       self.fname = "Liste"
       self.model =  QtGui.QStandardItemModel(self)

       self.tableView = QtWidgets.QTableView(self)
       self.tableView.setStyleSheet(stylesheet(self))
       self.tableView.setModel(self.model)
       self.tableView.horizontalHeader().setStretchLastSection(True)
       self.tableView.setShowGrid(True)
       self.tableView.setGeometry(10, 50, 780, 645)
       self.model.dataChanged.connect(self.finishedEdit)

       self.pushButtonLoad = QtWidgets.QPushButton(self)
       self.pushButtonLoad.setText("Load CSV")
       self.pushButtonLoad.clicked.connect(self.loadCsvAction)
       self.pushButtonLoad.setFixedWidth(80)
       self.pushButtonLoad.setStyleSheet(stylesheet(self))

       self.pushButtonWrite = QtWidgets.QPushButton(self)
       self.pushButtonWrite.setText("Save CSV")
       self.pushButtonWrite.clicked.connect(self.writeCsv)
       self.pushButtonWrite.setFixedWidth(80)
       self.pushButtonWrite.setStyleSheet(stylesheet(self))

       self.pushButtonPreview = QtWidgets.QPushButton(self)
       self.pushButtonPreview.setText("Print Preview")
       self.pushButtonPreview.clicked.connect(self.handlePreview)
       self.pushButtonPreview.setFixedWidth(80)
       self.pushButtonPreview.setStyleSheet(stylesheet(self))

       self.pushButtonPrint = QtWidgets.QPushButton(self)
       self.pushButtonPrint.setText("Print")
       self.pushButtonPrint.clicked.connect(self.handlePrint)
       self.pushButtonPrint.setFixedWidth(80)
       self.pushButtonPrint.setStyleSheet(stylesheet(self))

       self.pushAddRow = QtWidgets.QPushButton(self)
       self.pushAddRow.setText("add Row")
       self.pushAddRow.clicked.connect(self.addRow)
       self.pushAddRow.setFixedWidth(80)
       self.pushAddRow.setStyleSheet(stylesheet(self))

       self.pushDeleteRow = QtWidgets.QPushButton(self)
       self.pushDeleteRow.setText("delete Row")
       self.pushDeleteRow.clicked.connect(self.removeRow)
       self.pushDeleteRow.setFixedWidth(80)
       self.pushDeleteRow.setStyleSheet(stylesheet(self))

       self.pushAddColumn = QtWidgets.QPushButton(self)
       self.pushAddColumn.setText("add Column")
       self.pushAddColumn.clicked.connect(self.addColumn)
       self.pushAddColumn.setFixedWidth(80)
       self.pushAddColumn.setStyleSheet(stylesheet(self))

       self.pushDeleteColumn = QtWidgets.QPushButton(self)
       self.pushDeleteColumn.setText("delete Column")
       self.pushDeleteColumn.clicked.connect(self.removeColumn)
       self.pushDeleteColumn.setFixedWidth(86)
       self.pushDeleteColumn.setStyleSheet(stylesheet(self))

       self.pushClear = QtWidgets.QPushButton(self)
       self.pushClear.setText("Clear")
       self.pushClear.clicked.connect(self.clearList)
       self.pushClear.setFixedWidth(60)
       self.pushClear.setStyleSheet(stylesheet(self))

       grid = QtWidgets.QGridLayout()
       grid.setSpacing(10)
       grid.addWidget(self.pushButtonLoad, 0, 0)
       grid.addWidget(self.pushButtonWrite, 0, 1)
       grid.addWidget(self.pushAddRow, 0, 2)
       grid.addWidget(self.pushDeleteRow, 0, 3)
       grid.addWidget(self.pushAddColumn, 0, 4)
       grid.addWidget(self.pushDeleteColumn, 0, 5)
       grid.addWidget(self.pushClear, 0, 6)
       grid.addWidget(self.pushButtonPreview, 0, 7)
       grid.addWidget(self.pushButtonPrint, 0, 8, 1, 1, QtCore.Qt.AlignRight)
       grid.addWidget(self.tableView, 1, 0, 1, 9)
       self.setLayout(grid)

       item = QtGui.QStandardItem()
       self.model.appendRow(item)
       self.model.setData(self.model.index(0, 0), "", 0)
       self.tableView.resizeColumnsToContents()

       if fileName!='':
           self.loadCsv(fileName)

   def loadCsvAction(self):
       fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open CSV",
               (QtCore.QDir.homePath()), "CSV (*.csv *.tsv)")
       if fileName:
            self.loadCsv(fileName)

   def loadCsv(self, fileName):
           print(fileName)
           ff = open(fileName, 'r')
           mytext = ff.read()
#            print(mytext)
           ff.close()
           f = open(fileName, 'r')
           with f:
               self.fname = os.path.splitext(str(fileName))[0].split("/")[-1]
               self.setWindowTitle(self.fname)
               if mytext.count(';') <= mytext.count('\t'):
                   reader = csv.reader(f, delimiter = '\t')
                   self.model.clear()
                   for row in reader:
                       items = [QtGui.QStandardItem(field) for field in row]
                       self.model.appendRow(items)
                   self.tableView.resizeColumnsToContents()
               else:
                   reader = csv.reader(f, delimiter = ';')
                   self.model.clear()
                   for row in reader:
                       items = [QtGui.QStandardItem(field) for field in row]
                       self.model.appendRow(items)
                   self.tableView.resizeColumnsToContents()

   def writeCsv(self, fileName):
       # find empty cells
       for row in range(self.model.rowCount()):
           for column in range(self.model.columnCount()):
               myitem = self.model.item(row,column)
               if myitem is None:
                   item = QtGui.QStandardItem("")
                   self.model.setItem(row, column, item)
       fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save File",
                       (QtCore.QDir.homePath() + "/" + self.fname + ".csv"),"CSV Files (*.csv)")
       if fileName:
           print(fileName)
           f = open(fileName, 'w')
           with f:
               writer = csv.writer(f, delimiter = '\t')
               for rowNumber in range(self.model.rowCount()):
                   fields = [self.model.data(self.model.index(rowNumber, columnNumber),
                                        QtCore.Qt.DisplayRole)
                    for columnNumber in range(self.model.columnCount())]
                   writer.writerow(fields)
               self.fname = os.path.splitext(str(fileName))[0].split("/")[-1]
               self.setWindowTitle(self.fname)

   def handlePrint(self):
       dialog = QtPrintSupport.QPrintDialog()
       if dialog.exec_() == QtWidgets.QDialog.Accepted:
           self.handlePaintRequest(dialog.printer())

   def handlePreview(self):
       dialog = QtPrintSupport.QPrintPreviewDialog()
       dialog.setFixedSize(1000,700)
       dialog.paintRequested.connect(self.handlePaintRequest)
       dialog.exec_()

   def handlePaintRequest(self, printer):
       # find empty cells
       for row in range(self.model.rowCount()):
           for column in range(self.model.columnCount()):
               myitem = self.model.item(row,column)
               if myitem is None:
                   item = QtGui.QStandardItem("")
                   self.model.setItem(row, column, item)
       printer.setDocName(self.fname)
       document = QtGui.QTextDocument()
       cursor = QtGui.QTextCursor(document)
       model = self.tableView.model()
       table = cursor.insertTable(model.rowCount(), model.columnCount())
       for row in range(table.rows()):
           for column in range(table.columns()):
               cursor.insertText(model.item(row, column).text())
               cursor.movePosition(QtGui.QTextCursor.NextCell)
       document.print_(printer)

   def removeRow(self):
       model = self.model
       indices = self.tableView.selectionModel().selectedRows()
       for index in sorted(indices):
           model.removeRow(index.row())

   def addRow(self):
       item = QtGui.QStandardItem("")
       self.model.appendRow(item)

   def clearList(self):
       self.model.clear()

   def removeColumn(self):
       model = self.model
       indices = self.tableView.selectionModel().selectedColumns()
       for index in sorted(indices):
           model.removeColumn(index.column())

   def addColumn(self):
       count = self.model.columnCount()
       print (count)
       self.model.setColumnCount(count + 1)
       self.model.setData(self.model.index(0, count), "", 0)
       self.tableView.resizeColumnsToContents()

   def finishedEdit(self):
       self.tableView.resizeColumnsToContents()

   def contextMenuEvent(self, event):
       self.menu = QtWidgets.QMenu(self)
       # copy
       copyAction = QtWidgets.QAction('Copy', self)
       copyAction.triggered.connect(lambda: self.copyByContext(event))
       # paste
       pasteAction = QtWidgets.QAction('Paste', self)
       pasteAction.triggered.connect(lambda: self.pasteByContext(event))
       # cut
       cutAction = QtWidgets.QAction('Cut', self)
       cutAction.triggered.connect(lambda: self.cutByContext(event))
       # delete selected Row
       removeAction = QtWidgets.QAction('delete Row', self)
       removeAction.triggered.connect(lambda: self.deleteRowByContext(event))
       # add Row after
       addAction = QtWidgets.QAction('insert new Row after', self)
       addAction.triggered.connect(lambda: self.addRowByContext(event))
       # add Row before
       addAction2 = QtWidgets.QAction('insert new Row before', self)
       addAction2.triggered.connect(lambda: self.addRowByContext2(event))
       # add Column before
       addColumnBeforeAction = QtWidgets.QAction('insert new Column before', self)
       addColumnBeforeAction.triggered.connect(lambda: self.addColumnBeforeByContext(event))
       # add Column after
       addColumnAfterAction = QtWidgets.QAction('insert new Column after', self)
       addColumnAfterAction.triggered.connect(lambda: self.addColumnAfterByContext(event))
       # delete Column
       deleteColumnAction = QtWidgets.QAction('delete Column', self)
       deleteColumnAction.triggered.connect(lambda: self.deleteColumnByContext(event))
       # add other required actions
       self.menu.addAction(copyAction)
       self.menu.addAction(pasteAction)
       self.menu.addAction(cutAction)
       self.menu.addSeparator()
       self.menu.addAction(addAction)
       self.menu.addAction(addAction2)
       self.menu.addSeparator()
       self.menu.addAction(addColumnBeforeAction)
       self.menu.addAction(addColumnAfterAction)
       self.menu.addSeparator()
       self.menu.addAction(removeAction)
       self.menu.addAction(deleteColumnAction)
       self.menu.popup(QtGui.QCursor.pos())

   def deleteRowByContext(self, event):
       for i in self.tableView.selectionModel().selection().indexes():
           row = i.row()
           self.model.removeRow(row)
           print("Row " + str(row) + " deleted")
           self.tableView.selectRow(row)

   def addRowByContext(self, event):
       for i in self.tableView.selectionModel().selection().indexes():
           row = i.row() + 1
           self.model.insertRow(row)
           print("Row at " + str(row) + " inserted")
           self.tableView.selectRow(row)

   def addRowByContext2(self, event):
       for i in self.tableView.selectionModel().selection().indexes():
           row = i.row()
           self.model.insertRow(row)
           print("Row at " + str(row) + " inserted")
           self.tableView.selectRow(row)

   def addColumnBeforeByContext(self, event):
       for i in self.tableView.selectionModel().selection().indexes():
           col = i.column()
           self.model.insertColumn(col)
           print("Column at " + str(col) + " inserted")

   def addColumnAfterByContext(self, event):
       for i in self.tableView.selectionModel().selection().indexes():
           col = i.column() + 1
           self.model.insertColumn(col)
           print("Column at " + str(col) + " inserted")

   def deleteColumnByContext(self, event):
       for i in self.tableView.selectionModel().selection().indexes():
           col = i.column()
           self.model.removeColumn(col)
           print("Column at " + str(col) + " removed")

   def copyByContext(self, event):
       for i in self.tableView.selectionModel().selection().indexes():
           row = i.row()
           col = i.column()
           myitem = self.model.item(row,col)
           if myitem is not None:
               clip = QtWidgets.QApplication.clipboard()
               clip.setText(myitem.text())

   def pasteByContext(self, event):
       for i in self.tableView.selectionModel().selection().indexes():
           row = i.row()
           col = i.column()
           myitem = self.model.item(row,col)
           clip = QtWidgets.QApplication.clipboard()
           myitem.setText(clip.text())

   def cutByContext(self, event):
       for i in self.tableView.selectionModel().selection().indexes():
           row = i.row()
           col = i.column()
           myitem = self.model.item(row,col)
           if myitem is not None:
               clip = QtWidgets.QApplication.clipboard()
               clip.setText(myitem.text())
               myitem.setText("")

def stylesheet(self):
       return """
       QTableView
       {
border: 1px solid grey;
border-radius: 0px;
font-size: 12px;
        background-color: #f8f8f8;
selection-color: white;
selection-background-color: #00ED56;
       }

QTableView QTableCornerButton::section {
    background: #D6D1D1;
    border: 1px outset black;
}

QPushButton
{
font-size: 11px;
border: 1px inset grey;
height: 24px;
width: 80px;
color: black;
background-color: #e8e8e8;
background-position: bottom-left;
}

QPushButton::hover
{
border: 2px inset goldenrod;
font-weight: bold;
color: #e8e8e8;
background-color: green;
}
"""

if __name__ == "__main__":
   import sys

   app = QtWidgets.QApplication(sys.argv)
   app.setApplicationName('MyWindow')
   main = MyWindow('testdaten2.csv')
   main.setMinimumSize(820, 300)
   main.setGeometry(0,0,820,700)
   main.setWindowTitle("CSV Viewer")
   main.show()

sys.exit(app.exec_())
