# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CopernicusData
                                 A QGIS plugin
 This plugin downloads data using the cdsapi
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-01-21
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Fredrik Lindberg
        email                : fredrikl@gvc.gu.se
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QObject, pyqtSignal, QThread
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.gui import QgsMapToolEmitPoint
from osgeo import osr, ogr, gdal
import os.path
import webbrowser
import datetime
from calendar import monthrange
from .WorkerDownload import DownloadDataWorker

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .copernicus_data_dialog import CopernicusDataDialog


class CopernicusData:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CopernicusData_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.dlg = CopernicusDataDialog()
        self.dlg.cmdSelectPoint.clicked.connect(self.select_point)
        self.dlg.cmdRunDownload.clicked.connect(self.download)
        self.dlg.pushButtonHelp.clicked.connect(self.help)
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(QFileDialog.Directory)
        self.fileDialog.setOption(QFileDialog.ShowDirsOnly, True)

        self.dlg.progressBar.setRange(0, 100)
        self.dlg.progressBar.setValue(0)

        # Parameters for downloader
        self.lat = None
        self.lon = None
        self.start_date = None
        self.end_date = None
        self.save_downloaded_file = None

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Copernicus Data')

        # get reference to the canvas
        self.canvas = self.iface.mapCanvas()
        self.degree = 5.0
        self.point = None
        self.pointx = None
        self.pointy = None

        # #g pin tool
        self.pointTool = QgsMapToolEmitPoint(self.canvas)
        self.pointTool.canvasClicked.connect(self.create_point)

        self.folderPath = None
        self.save_downloaded_folder = None
        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        #self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CopernicusData', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/copernicus_data/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        # self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Copernicus Data'),
                action)
            self.iface.removeToolBarIcon(action)

    def help(self):
        url = "https://umep-docs.readthedocs.io/en/latest/pre-processor/Meteorological%20Data%20Download%20data%20(ERA5).html"
        webbrowser.open_new_tab(url)

    def select_point(self):  # Connected to "Seelct Point on Canves"
        # Calls a canvas click and create_point
        self.canvas.setMapTool(self.pointTool)
        self.dlg.setEnabled(False)

    def create_point(self, point):
        # report map coordinates from a canvas click
        self.dlg.setEnabled(True)
        self.dlg.activateWindow()

        canvas = self.iface.mapCanvas()
        srs = canvas.mapSettings().destinationCrs()
        crs = str(srs.authid())
        old_cs = osr.SpatialReference()
        old_cs.ImportFromEPSG(int(crs[5:]))

        new_cs = osr.SpatialReference()
        new_cs.ImportFromEPSG(4326)

        transform = osr.CoordinateTransformation(old_cs, new_cs)

        latlon = ogr.CreateGeometryFromWkt(
            'POINT (' + str(point.x()) + ' ' + str(point.y()) + ')')
        latlon.Transform(transform)

        gdalver = float(gdal.__version__[0])
        if gdalver == 3.:
            self.dlg.txtLon.setText(str(latlon.GetY())) # changed to gdal 3
            self.dlg.txtLat.setText(str(latlon.GetX())) # changed to gdal 3
        else:
            self.dlg.txtLon.setText(str(latlon.GetX())) # changed to gdal 2
            self.dlg.txtLat.setText(str(latlon.GetY())) # changed to gdal 2

        self.dlg.progressBar.setValue(0)

    def run(self):
        # Check the more unusual dependencies to prevent confusing errors later
        try:
            import supy as sp
        except Exception as e:
            QMessageBox.critical(None, 'Error', 'This plugin requires the supy package '
                                                'to be installed OR upgraded. Please consult the FAQ in the manual '
                                                'for further information on how to install missing python packages.')
            return

        if not (os.path.isfile(os.path.expanduser("~") + "/.cdsapirc")):
            QMessageBox.critical(None, 'CDS configuration missing', 'This plugin requires that you have configured your computer to use the CDS API. '
                                 'See the help section for the Copernicus plugin in the UMEP-manual for further information on how '
                                 'to make use of this plugin.')
            return

        self.dlg.show()
        self.dlg.exec_()

    def validate_downloader_input(self):
        """Validates user input for downloader section of form. Raises exception if a problem, commits
        parameters to object if OK"""

        # validate and record the latitude and longitude boxes (must be WGS84)
        try:
            lon = float(self.dlg.txtLon.text())
        except:
            raise ValueError('Invalid longitude co-ordinate entered')

        if not (-180 < lon < 180):
            raise ValueError(
                'Invalid longitude co-ordinate entered (must be -180 to 180)')

        try:
            lat = float(self.dlg.txtLat.text())
        except:
            raise ValueError('Invalid latitude co-ordinate entered')
        if not (-90 < lat < 90):
            raise ValueError(
                'Invalid latitude co-ordinate entered (must be -90 to 90)')

        self.lat = lat 
        self.lon = lon 

        # validate date range and add to object properties if OK
        start_date = self.dlg.txtStartDate.text()
        try:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        except Exception:
            raise ValueError('Invalid start date (%s) entered' % (start_date,))

        end_date = self.dlg.txtEndDate.text()
        try:
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        except Exception:
            raise ValueError('Invalid end date (%s) entered' % (end_date,))

        if start_date >= end_date:
            raise ValueError('Start date is greater or equal than end date')

        self.start_date = start_date
        self.end_date = end_date

    def folder_path(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            # self.dlg.textOutput.setText(self.folderPath[0])
            self.save_downloaded_folder = self.folderPath[0]

    def download(self):
        if QMessageBox.question(self.iface.mainWindow(), "Information", "Data will now be downloaded from the "
                                "Copernicus project (https://cds.climate.copernicus.eu/)."
                                "\r\n"
                                "\r\n"
                                "1 month of data takes about 6 minutes depending on traffic"
                                "and your internet connection."
                                "\r\n"
                                "\r\n"
                                "The QGIS session will be active while data is processed."
                                "\r\n"
                                "\r\n"
                                "Do you want to contiune?",
                                QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok:
                                test=4
        else:
            QMessageBox.critical(self.iface.mainWindow(), "Process aborted", "Download cancelled")
            return

            # Downloads ERA5 data
        try:
            self.validate_downloader_input()  # Validate input co-ordinates and time range
            # Before starting, ask user where to save
            self.folder_path()
            if (self.folderPath is None) or (len(self.folderPath) == 0):
                return
        except Exception as e:
            QMessageBox.critical(None, "Error", str(e))
            return

        # print(self.lat)
        # print(self.lon)
        # print(self.start_date)
        # print(self.end_date)
        # print(self.folderPath[0])
        self.dlg.progressBar.setValue(50)
        # return

        # put in worker
        # sp.util.download_era5(self.lat, self.lon, "2001-01-10", "2001-01-12") #, dir_save=self.plugin_dir
        # sp.util.gen_forcing_era5(self.lat, self.lon, "2001-01-10", "2001-01-12") #, dir_save=self.plugin_dir)

        # Do download in separate thread and track progress
        self.dlg.cmdRunDownload.clicked.disconnect()
        self.dlg.cmdRunDownload.setText('Cancel')
        downloadWorker = DownloadDataWorker(self.start_date, self.end_date, self.folderPath, self.lat, self.lon)
        thr = QThread(self.dlg)
        downloadWorker.moveToThread(thr)
        downloadWorker.update.connect(self.update_progress)
        downloadWorker.error.connect(self.download_error)
        downloadWorker.finished.connect(self.downloadWorkerFinished)
        thr.started.connect(downloadWorker.run)
        thr.start()
        self.downloadThread = thr
        self.downloadWorker = downloadWorker

        self.dlg.cmdRunDownload.clicked.connect(self.abort_download)
        self.dlg.progressBar.setValue(100)

    def update_progress(self, returns):
        # Updates progress bar during download
        self.dlg.progressBar.setValue(returns['progress'])

    def download_error(self, exception, text):
        self.setDownloaderButtonState(True)
        QMessageBox.critical(
            None, "Error", 'Data download not completed: %s' % (str(exception),))

    def abort_download(self):
        self.downloadWorker.kill()
        # Enable all buttons in downloader.
        self.setDownloaderButtonState(True)
        self.dlg.cmdRunDownload.clicked.disconnect()
        self.dlg.cmdRunDownload.setText('Run')
        self.dlg.cmdRunDownload.clicked.connect(self.download)
        self.dlg.progressBar.setValue(0)

    def downloadWorkerFinished(self):
        self.downloadWorker.deleteLater()
        self.downloadThread.quit()
        self.downloadThread.wait()
        self.downloadThread.deleteLater()
        # Ask the user where they'd like to save the file
        self.setDownloaderButtonState(True)  # Enable all buttons
        self.dlg.cmdRunDownload.clicked.disconnect()
        self.dlg.cmdRunDownload.setText('Run')
        self.dlg.cmdRunDownload.clicked.connect(self.download)

        # Update the UI to reflect the saved file
        self.dlg.lblSavedDownloaded.setText(self.folderPath[0])

    def setDownloaderButtonState(self, state):
        ''' Enable or disable all dialog buttons in downloader section
        :param state: boolean: True or False. Reflects button state'''
        self.dlg.cmdSelectPoint.setEnabled(state)
        self.dlg.cmdRunDownload.setEnabled(state)
        self.dlg.cmdClose.setEnabled(state)
        self.dlg.txtLat.setEnabled(state)
        self.dlg.txtLon.setEnabled(state)
        self.dlg.txtStartDate.setEnabled(state)
        self.dlg.txtEndDate.setEnabled(state)