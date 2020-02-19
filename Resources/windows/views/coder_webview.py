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

class CoderWebView(QWebView, updates.UpdateInterface):

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
        # Export self as a javascript object in webview
        self.page().mainFrame().addToJavaScriptWindowObject('timeline', self)
        self.page().mainFrame().addToJavaScriptWindowObject('mainWindow', self.window)


    def __init__(self, window):
        QWebView.__init__(self)
        self.window = window
        #self.setAcceptDrops(True)
        #self.setAcceptDrops()

        # Get settings
        self.settings_obj = settings.get_settings()

        # Add self as listener to project data updates (used to update the timeline)
        get_app().updates.add_listener(self)

        # set url from configuration (QUrl takes absolute paths for file system paths, create from QFileInfo)
        self.setUrl(QUrl.fromLocalFile(QFileInfo(self.html_path).absoluteFilePath()))
        
        # Connect signal of javascript initialization to our javascript reference init function
        self.page().mainFrame().javaScriptWindowObjectCleared.connect(self.setup_js_data)


    
