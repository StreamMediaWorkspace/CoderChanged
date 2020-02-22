import os
import sys
from copy import deepcopy
from functools import partial
from random import uniform
from urllib.parse import urlparse
from operator import itemgetter

from PyQt5.QtCore import *
from PyQt5.QtGui import QCursor, QKeySequence
from PyQt5.QtWebKitWidgets import QWebView
from PyQt5.QtWidgets import QMenu

from classes import info, updates
from classes import settings
from classes.app import get_app
from classes.logger import log

from windows.node_editor import NodeEditor

try:
    import json
except ImportError:
    import simplejson as json

class CoderWebView(QWebView, updates.UpdateInterface):
    # Path to html file
    html_path = os.path.join(info.PATH, 'coderview', 'index.html')

    @pyqtSlot()
    def page_ready(self):
        """Document.Ready event has fired, and is initialized"""
        self.document_is_ready = True
        log.info("coder page ready")

    def eval_js(self, code):
        # Check if document.Ready has fired in JS
        if not self.document_is_ready:
            # Not ready, try again in a few milliseconds
            log.error("CoderWebView::eval_js() called before document ready event. Script queued: %s" % code)
            QTimer.singleShot(50, partial(self.eval_js, code))
            return None
        else:
            # Execute JS code
            return self.page().mainFrame().evaluateJavaScript(code)

    def setup_js_data(self):
        #print("=========coder webview====setup_js_data====")
        # Export self as a javascript object in webview
        self.page().mainFrame().addToJavaScriptWindowObject('coderview', self)
        self.page().mainFrame().addToJavaScriptWindowObject('mainWindow', self.window)

    @pyqtSlot(str)
    def qt_log(self, message=None):
        log.info(message)

    # This method is invoked by the UpdateManager each time a change happens (i.e UpdateInterface)
    def changed(self, action):
        # Remove unused action attribute (old_values)
        action = deepcopy(action)
        action.old_values = {}
        
        if action.type == "load":
            project = get_app().project
            coder = project.get(["coder"])
        
            nodes = coder["nodes"]
            edges = coder["edges"]
            for node in nodes:
                self.eval_js("addNode('"+json.dumps(node)+"');")
            
            for edge in edges:
                self.eval_js("addEdge('"+json.dumps(edge)+"');")

        '''
        # Send a JSON version of the UpdateAction to the timeline webview method: ApplyJsonDiff()
        if action.type == "load":
            # Initialize translated track name
            _ = get_app()._tr
            self.eval_js(JS_SCOPE_SELECTOR + ".SetTrackLabel('" + _("Track %s") + "');")

            # Load entire project data
            code = JS_SCOPE_SELECTOR + ".LoadJson(" + action.json() + ");"
        else:
            # Apply diff to part of project data
            code = JS_SCOPE_SELECTOR + ".ApplyJsonDiff([" + action.json() + "]);"
        self.eval_js(code)

        # Reset the scale when loading new JSON
        if action.type == "load":
            # Set the scale again (to project setting)
            initial_scale = get_app().project.get(["scale"]) or 15
            get_app().window.sliderZoom.setValue(secondsToZoom(initial_scale))
        '''

    @pyqtSlot(str)
    def onNodeAdded(self, n):
        project = get_app().project
        coder = project.get(["coder"])
        nodes = coder["nodes"]
        n = json.loads(n)
        node = {"id": n["id"], "text": n["text"], "x": n["x"], "y": n["y"], "nodeType": 0, "color": n["color"]}
        nodes.append(node)
        print("=======", nodes)
    
    @pyqtSlot(str)
    def onNodeUpdate(self, n):
        project = get_app().project
        coder = project.get(["coder"])
        nodes = coder["nodes"]
        n = json.loads(n)
        for node in nodes:
            if node["id"] == n["id"]:
                node["x"] = n["x"]
                node["y"] = n["y"]
        print("====onNodeUpdate===", nodes)

    @pyqtSlot(str)
    def onNodeDoubleClicked(self, nodeId):
        print("=====onNodeDoubleClicked====", nodeId)
        #self.getSelectedNodes()
        edge = self.getEdgeByFromNodeId(nodeId)
        nodeEditor = NodeEditor(self.getNodeById(nodeId), edge)
        nodeEditor.exec_()
        if nodeEditor.Accept:
            text = nodeEditor.lineEditText.text()
            self.updateNodeText(nodeId, text)
            log.info('NodeEditor Finished')

            to_node = nodeEditor.comboBoxToNode.itemData(nodeEditor.comboBoxToNode.currentIndex())
            print("=====----", to_node)
            edge_id = -1
            if edge:
                edge_id = edge.id
            self.updateEdge(edge_id, nodeId, to_node)
        else:
            log.info('NodeEditor Cancelled')


    def getSelectedNodes(self):
        selected_nodes = []
        node_json = self.eval_js("getSelectedCoder();")
        project = get_app().project
        coder = project.get(["coder"])
        nodes = coder["nodes"]
        ids = json.loads(node_json)
        for id in ids:
            for node in nodes:
                if node["id"] == id:
                    selected_nodes.append(node)
                    break
        print("====getSelectedNodes===", selected_nodes)
        return selected_nodes

    
    def updateNodeText(self, id, value):
        self.eval_js("updateNodeText('" + str(id) + "', '" + value + "');")

    def onUpdateNodeText(self, id, value):
        self.updateNodeObject(id, "text", value)

    def updateEdge(self, id, from_node, to):
        self.eval_js("updateEdge('" + str(id) + "', '" + from_node + "', '" + to + "');")


    def updateNodeObject(self, id, key, value):
        project = get_app().project
        coder = project.get(["coder"])
        nodes = coder["nodes"]
        for node in nodes:
            if node["id"] == id:
                node[key] = value
                return True
        
        return False
       

    def getNodeById(self, id):
        project = get_app().project
        coder = project.get(["coder"])
        nodes = coder["nodes"]

        for node in nodes:
            if node["id"] == id:
                return node
        return None

    def getEdgeByFromNodeId(self, id):
        project = get_app().project
        coder = project.get(["coder"])
        edges = coder["edges"]

        for edge in edges:
            if edge["from"] == id:
                return edge
        return None

    def __init__(self, window):
        QWebView.__init__(self)
        self.document_is_ready = False
        self.window = window
        self.setAcceptDrops(True)

        # Get settings
        self.settings_obj = settings.get_settings()

        # Add self as listener to project data updates (used to update the timeline)
        get_app().updates.add_listener(self)

        # set url from configuration (QUrl takes absolute paths for file system paths, create from QFileInfo)
        self.setUrl(QUrl.fromLocalFile(QFileInfo(self.html_path).absoluteFilePath()))

        # Connect signal of javascript initialization to our javascript reference init function
        self.page().mainFrame().javaScriptWindowObjectCleared.connect(self.setup_js_data)


    
