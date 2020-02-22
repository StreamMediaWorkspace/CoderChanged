import os
import sys
import functools
import math

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import openshot  # Python module for libopenshot (required video editing module installed separately)

from classes import info, ui_util, settings, qt_types, updates
from classes.app import get_app
from classes.logger import log
from classes.metrics import *
from classes.query import Clip, Cut

try:
    import json
except ImportError:
    import simplejson as json

class NodeEditor(QDialog):
    """ NodeEditor Dialog """

    # Path to ui file
    ui_path = os.path.join(info.PATH, 'windows', 'ui', 'node-editor.ui')

    def __init__(self, node, edge=None):
        _ = get_app()._tr

        # Create dialog class
        QDialog.__init__(self)

        # Load UI from designer
        ui_util.load_ui(self, self.ui_path)

        # Init UI
        ui_util.init_ui(self)

        self.node = node
        self.edge = edge
        self.Accept = False


        self.pushButtonOK.clicked.connect(self.onAccept)
        self.pushButtonCancel.clicked.connect(self.onCancel)
        self.lineEditText.setText(node["text"])

        project = get_app().project
        coder = project.get(["coder"])
        nodes = coder["nodes"]
        for node in nodes:
            if node["nodeType"] != 1:
                self.comboBoxToNode.addItem(node["text"], node["id"])

        if edge:
            to_node = self.getNodeNameById(edge["to"])
            if to_node:
                self.comboBoxToNode.setCurrentText(to_node["text"])
            else:
                self.comboBoxToNode.setCurrentText("no seleted")
        else:
            self.comboBoxToNode.setCurrentText("no seleted")

        
    def onAccept(self):
        self.Accept = True
        self.close()

    def onCancel(self):
        self.Accept = False
        self.close()

