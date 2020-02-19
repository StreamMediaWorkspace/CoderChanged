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

class CoderWebView(QWebView):

    # Path to html file
    html_path = os.path.join(info.PATH, 'coderview', 'index.html')

    @pyqtSlot()
    def page_ready(self):
        """Document.Ready event has fired, and is initialized"""
        self.document_is_ready = True

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
        return
        # Remove unused action attribute (old_values)
        action = deepcopy(action)
        action.old_values = {}

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

    def __init__(self, window):
        QWebView.__init__(self)
        self.window = window
        #self.setAcceptDrops(True)

        # Get settings
        self.settings_obj = settings.get_settings()

        # Add self as listener to project data updates (used to update the timeline)
        get_app().updates.add_listener(self)

        # set url from configuration (QUrl takes absolute paths for file system paths, create from QFileInfo)
        self.setUrl(QUrl.fromLocalFile(QFileInfo(self.html_path).absoluteFilePath()))

        # Connect signal of javascript initialization to our javascript reference init function
        self.page().mainFrame().javaScriptWindowObjectCleared.connect(self.setup_js_data)


    
