# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SOLWEIG
                                 A QGIS plugin
 Solar and longwave environmental irraniance model
                              -------------------
        begin                : 2016-09-06
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Fredrik Lindberg, UoG
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QThread
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
# import resources
# Import the code for the dialog
from solweig_dialog import SOLWEIGDialog
import numpy as np
from osgeo import gdal, osr
from ..Utilities.qgiscombomanager import *
import os.path
import zipfile
import webbrowser
from osgeo.gdalconst import *
from solweigworker import Worker

from SOLWEIGpython import Solweig_v2015_metdata_noload as metload
# from SOLWEIGpython import Solweig_2015a_calc as so
from SOLWEIGpython.Tgmaps_v1 import Tgmaps_v1
# from SOLWEIGpython.clearnessindex_2013b import clearnessindex_2013b

class SOLWEIG:
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
            'SOLWEIG_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = SOLWEIGDialog()
        self.dlg.pushButtonHelp.clicked.connect(self.help)
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path_out)
        self.fileDialog = QFileDialog()
        self.fileDialog.setFileMode(4)
        self.fileDialog.setAcceptMode(1)

        self.dlg.pushButtonImportMetData.clicked.connect(self.met_file)
        self.fileDialogMet = QFileDialog()
        self.fileDialogMet.setNameFilter("(*.txt)")

        self.dlg.pushButtonImportSVF.clicked.connect(self.svf_file)
        self.fileDialogSVF = QFileDialog()
        self.fileDialogSVF.setNameFilter("(svfs.zip)")

        # Declare instance attributes
        self.actions = []
        # self.menu = self.tr(u'&SOLWEIG')
        # TODO: We are going to let the user set this up in a future iteration
        # self.toolbar = self.iface.addToolBar(u'SOLWEIG')
        # self.toolbar.setObjectName(u'SOLWEIG')

        self.layerComboManagerDSM = RasterLayerCombo(self.dlg.comboBox_dsm)
        RasterLayerCombo(self.dlg.comboBox_dsm, initLayer="")
        self.layerComboManagerVEGDSM = RasterLayerCombo(self.dlg.comboBox_vegdsm)
        RasterLayerCombo(self.dlg.comboBox_vegdsm, initLayer="")
        self.layerComboManagerVEGDSM2 = RasterLayerCombo(self.dlg.comboBox_vegdsm2)
        RasterLayerCombo(self.dlg.comboBox_vegdsm2, initLayer="")
        self.layerComboManagerDEM = RasterLayerCombo(self.dlg.comboBox_dem)
        RasterLayerCombo(self.dlg.comboBox_dem, initLayer="")
        self.layerComboManagerLC = RasterLayerCombo(self.dlg.comboBox_landcover)
        RasterLayerCombo(self.dlg.comboBox_landcover, initLayer="")
        self.layerComboManagerWH = RasterLayerCombo(self.dlg.comboBox_wallheight)
        RasterLayerCombo(self.dlg.comboBox_wallheight, initLayer="")
        self.layerComboManagerWA = RasterLayerCombo(self.dlg.comboBox_wallaspect)
        RasterLayerCombo(self.dlg.comboBox_wallaspect, initLayer="")
        self.layerComboManagerPOI = VectorLayerCombo(self.dlg.comboBox_POIlayer)
        fieldgen = VectorLayerCombo(self.dlg.comboBox_POIlayer, initLayer="", options={"geomType": QGis.Point})
        self.layerComboManagerPOIfield = FieldCombo(self.dlg.comboBox_POIfield, fieldgen, initField="") #, options={"fieldType": int}

        self.folderPath = None
        self.folderPathSVF = None
        self.usevegdem = 0
        self.landcover = 0
        self.vegdsm = None
        self.vegdsm2 = None
        self.svfbu = None
        self.dsm = None
        self.scale = None
        self.steps = 0
        self.demforbuild = None
        self.dem = None
        self.lcgrid = None
        self.trans = None
        self.poisxy = None
        self.poiname = None

        self.thread = None
        self.worker = None
        self.steps = 0

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SOLWEIG', message)


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
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/SOLWEIG/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&SOLWEIG'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def folder_path_out(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            self.dlg.textOutput.setText(self.folderPath[0])

    def met_file(self):
        self.fileDialogMet.open()
        result = self.fileDialogMet.exec_()
        if result == 1:
            self.folderPathMet = self.fileDialogMet.selectedFiles()
            self.dlg.textInputMetdata.setText(self.folderPathMet[0])

    def svf_file(self):
        self.fileDialogSVF.open()
        result = self.fileDialogSVF.exec_()
        if result == 1:
            self.folderPathSVF = self.fileDialogSVF.selectedFiles()
            self.dlg.textInputSVF.setText(self.folderPathSVF[0])

    def read_metdata(self):
        headernum = 1
        delim = ' '
        try:
            self.metdata = np.loadtxt(self.folderPathMet[0], skiprows=headernum, delimiter=delim)
        except:
            QMessageBox.critical(self.dlg, "Import Error",
                                 "Make sure format of meteorological file is correct. You can "
                                 "prepare your data by using 'Prepare Existing Data' in "
                                 "the Pre-processor")
            return

        if self.metdata.shape[1] == 24:
            self.iface.messageBar().pushMessage("SOLWEIG", "Meteorological data succesfully loaded",
                                                level=QgsMessageBar.INFO, duration=3)
        else:
            QMessageBox.critical(self.dlg, "Import Error",
                                 "Wrong number of columns in meteorological data. You can "
                                 "prepare your data by using 'Prepare Existing Data' in "
                                 "the Pre-processor")
            return

    def day_of_year(self, yyyy, month, day):
        if (yyyy % 4) == 0:
            if (yyyy % 100) == 0:
                if (yyyy % 400) == 0:
                    leapyear = 1
                else:
                    leapyear = 0
            else:
                leapyear = 1
        else:
            leapyear = 0

        if leapyear == 1:
            dayspermonth = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        else:
            dayspermonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

        doy = np.sum(dayspermonth[0:month - 1]) + day

        return doy

    def progress_update(self):
        self.steps += 1
        self.dlg.progressBar.setValue(self.steps)

    def start_progress(self):
        self.steps = 0
        if self.folderPath is None:
            QMessageBox.critical(self.dlg, "Error", "No save folder selected")
        else:
            # self.dlg.textOutput.setText(self.folderPath[0])
            dsmlayer = self.layerComboManagerDSM.getLayer()

            if dsmlayer is None:
                QMessageBox.critical(self.dlg, "Error", "No valid ground and building DSM is selected")
                return

            provider = dsmlayer.dataProvider()
            filepath_dsm = str(provider.dataSourceUri())
            self.gdal_dsm = gdal.Open(filepath_dsm)
            self.dsm = self.gdal_dsm.ReadAsArray().astype(np.float)
            sizex = self.dsm.shape[0]  # rows
            sizey = self.dsm.shape[1]  # cols
            rows = self.dsm.shape[0]
            cols = self.dsm.shape[1]
            geotransform = self.gdal_dsm.GetGeoTransform()
            self.scale = 1 / geotransform[1]
            alt = self.dsm.mean()

            old_cs = osr.SpatialReference()
            dsm_ref = dsmlayer.crs().toWkt()
            old_cs.ImportFromWkt(dsm_ref)

            wgs84_wkt = """
                GEOGCS["WGS 84",
                    DATUM["WGS_1984",
                        SPHEROID["WGS 84",6378137,298.257223563,
                            AUTHORITY["EPSG","7030"]],
                        AUTHORITY["EPSG","6326"]],
                    PRIMEM["Greenwich",0,
                        AUTHORITY["EPSG","8901"]],
                    UNIT["degree",0.01745329251994328,
                        AUTHORITY["EPSG","9122"]],
                    AUTHORITY["EPSG","4326"]]"""

            new_cs = osr.SpatialReference()
            new_cs.ImportFromWkt(wgs84_wkt)

            transform = osr.CoordinateTransformation(old_cs, new_cs)

            width = self.gdal_dsm.RasterXSize
            height = self.gdal_dsm.RasterYSize
            minx = geotransform[0]
            miny = geotransform[3] + width * geotransform[4] + height * geotransform[5]
            lonlat = transform.TransformPoint(minx, miny)
            lon = lonlat[0]
            lat = lonlat[1]
            UTC = self.dlg.spinBoxUTC.value()

            if (sizex * sizey) > 250000 and (sizex * sizey) <= 1000000:
                QMessageBox.warning(self.dlg, "Semi lage grid",
                                    "This process will take a couple of minutes. "
                                    "Go and make yourself a cup of tea...")

            if (sizex * sizey) > 1000000 and (sizex * sizey) <= 4000000:
                QMessageBox.warning(self.dlg, "Large grid", "This process will take some time. "
                                                                           "Go for lunch...")

            if (sizex * sizey) > 4000000 and (sizex * sizey) <= 16000000:
                QMessageBox.warning(self.dlg, "Very large grid", "This process will take a long time. "
                                                                                "Go for lunch and for a walk...")

            if (sizex * sizey) > 16000000:
                QMessageBox.warning(self.dlg, "Huge grid", "This process will take a very long time. "
                                                                          "Go home for the weekend or consider to tile your grid")

            # Vegetation DSMs #
            if self.dlg.checkBoxUseVeg.isChecked():
                self.usevegdem = 1
                self.trans = self.dlg.spinBoxTrans.value() / 100.0

                self.vegdsm = self.layerComboManagerVEGDSM.getLayer()

                if self.vegdsm is None:
                    QMessageBox.critical(self.dlg, "Error", "No valid vegetation canopy DSM selected")
                    return

                # load raster
                gdal.AllRegister()
                provider = self.vegdsm.dataProvider()
                filePathOld = str(provider.dataSourceUri())
                dataSet = gdal.Open(filePathOld)
                self.vegdsm = dataSet.ReadAsArray().astype(np.float)

                vegsizex = self.vegdsm.shape[0]
                vegsizey = self.vegdsm.shape[1]

                if not (vegsizex == sizex) & (vegsizey == sizey):  # &
                    QMessageBox.critical(self.dlg, "Error in vegetation canopy DSM",
                                         "All grids must be of same extent and resolution")
                    return

                if self.dlg.checkBoxTrunkExist.isChecked():
                    self.vegdsm2 = self.layerComboManagerVEGDSM2.getLayer()

                    if self.vegdsm2 is None:
                        QMessageBox.critical(self.dlg, "Error", "No valid trunk zone DSM selected")
                        return

                    # load raster
                    gdal.AllRegister()
                    provider = self.vegdsm.dataProvider()
                    filePathOld = str(provider.dataSourceUri())
                    dataSet = gdal.Open(filePathOld)
                    self.vegdsm2 = dataSet.ReadAsArray().astype(np.float)
                else:
                    trunkratio = self.dlg.spinBoxTrunkHeight.value() / 100.0
                    self.vegdsm2 = self.vegdsm * trunkratio
                    if self.dlg.checkBoxSaveTrunk.isChecked():
                        self.saveraster(self.gdal_dsm, self.folderPath[0] + '/TDSM.tif', self.vegdsm2)

                vegsizex = self.vegdsm2.shape[0]
                vegsizey = self.vegdsm2.shape[1]

                if not (vegsizex == sizex) & (vegsizey == sizey):  # &
                    QMessageBox.critical(self.dlg, "Error in trunk zone DSM",
                                         "All grids must be of same extent and resolution")
                    return

            else:
                self.vegdsm = np.zeros([rows, cols])
                self.vegdsm2 = np.zeros([rows, cols])
                self.usevegdem = 0

            # Land cover #
            if self.dlg.checkBoxLandCover.isChecked():
                self.landcover = 1
                self.demforbuild = 0

                self.lcgrid = self.layerComboManagerLC.getLayer()

                if self.lcgrid is None:
                    QMessageBox.critical(self.dlg, "Error", "No valid land cover grid is selected")
                    return

                # load raster
                gdal.AllRegister()
                provider = self.lcgrid.dataProvider()
                filePathOld = str(provider.dataSourceUri())
                dataSet = gdal.Open(filePathOld)
                self.lcgrid = dataSet.ReadAsArray().astype(np.float)

                lcsizex = self.lcgrid.shape[0]
                lcsizey = self.lcgrid.shape[1]

                if not (lcsizex == sizex) & (lcsizey == sizey):
                    QMessageBox.critical(self.dlg, "Error in land cover grid",
                                         "All grids must be of same extent and resolution")
                    return
            #else:
            #    self.lcgrid = np.zeros([rows, cols])

            # DEM #
            if not self.dlg.checkBoxDEM.isChecked():
                self.demforbuild = 1

                self.dem = self.layerComboManagerDEM.getLayer()

                if self.dem is None:
                    QMessageBox.critical(self.dlg, "Error", "No valid DEM selected")
                    return

                # load raster
                gdal.AllRegister()
                provider = self.dem.dataProvider()
                filePathOld = str(provider.dataSourceUri())
                dataSet = gdal.Open(filePathOld)
                self.dem = dataSet.ReadAsArray().astype(np.float)

                demsizex = self.dem.shape[0]
                demsizey = self.dem.shape[1]

                if not (demsizex == sizex) & (demsizey == sizey):
                    QMessageBox.critical(self.dlg, "Error in DEM", "All grids must be of same extent and resolution")
                    return

                alt = self.dem.mean()

            # SVFs #
            if self.folderPathSVF is None:
                QMessageBox.critical(self.dlg, "Error", "No SVF zipfile is selected. Use the Sky View Factor"
                                                        "Calculator to generate svf.zip")
                return
            else:
                zip = zipfile.ZipFile(self.folderPathSVF[0], 'r')
                zip.extractall(self.plugin_dir)
                zip.close()

                try:
                    dataSet = gdal.Open(self.plugin_dir + "/svf.tif")
                    svf = dataSet.ReadAsArray().astype(np.float)
                    dataSet = gdal.Open(self.plugin_dir + "/svfN.tif")
                    svfN = dataSet.ReadAsArray().astype(np.float)
                    dataSet = gdal.Open(self.plugin_dir + "/svfS.tif")
                    svfS = dataSet.ReadAsArray().astype(np.float)
                    dataSet = gdal.Open(self.plugin_dir + "/svfE.tif")
                    svfE = dataSet.ReadAsArray().astype(np.float)
                    dataSet = gdal.Open(self.plugin_dir + "/svfW.tif")
                    svfW = dataSet.ReadAsArray().astype(np.float)

                    if self.usevegdem == 1:
                        dataSet = gdal.Open(self.plugin_dir + "/svfveg.tif")
                        svfveg = dataSet.ReadAsArray().astype(np.float)
                        dataSet = gdal.Open(self.plugin_dir + "/svfNveg.tif")
                        svfNveg = dataSet.ReadAsArray().astype(np.float)
                        dataSet = gdal.Open(self.plugin_dir + "/svfSveg.tif")
                        svfSveg = dataSet.ReadAsArray().astype(np.float)
                        dataSet = gdal.Open(self.plugin_dir + "/svfEveg.tif")
                        svfEveg = dataSet.ReadAsArray().astype(np.float)
                        dataSet = gdal.Open(self.plugin_dir + "/svfWveg.tif")
                        svfWveg = dataSet.ReadAsArray().astype(np.float)

                        dataSet = gdal.Open(self.plugin_dir + "/svfaveg.tif")
                        svfaveg = dataSet.ReadAsArray().astype(np.float)
                        dataSet = gdal.Open(self.plugin_dir + "/svfNaveg.tif")
                        svfNaveg = dataSet.ReadAsArray().astype(np.float)
                        dataSet = gdal.Open(self.plugin_dir + "/svfSaveg.tif")
                        svfSaveg = dataSet.ReadAsArray().astype(np.float)
                        dataSet = gdal.Open(self.plugin_dir + "/svfEaveg.tif")
                        svfEaveg = dataSet.ReadAsArray().astype(np.float)
                        dataSet = gdal.Open(self.plugin_dir + "/svfWaveg.tif")
                        svfWaveg = dataSet.ReadAsArray().astype(np.float)
                    else:
                        svfveg = np.ones((rows, cols))
                        svfNveg = np.ones((rows, cols))
                        svfSveg = np.ones((rows, cols))
                        svfEveg = np.ones((rows, cols))
                        svfWveg = np.ones((rows, cols))
                        svfaveg = np.ones((rows, cols))
                        svfNaveg = np.ones((rows, cols))
                        svfSaveg = np.ones((rows, cols))
                        svfEaveg = np.ones((rows, cols))
                        svfWaveg = np.ones((rows, cols))
                except:
                    QMessageBox.critical(self.dlg, "SVF import error", "The zipfile including the SVFs seems corrupt. "
                                                                   "Retry calcualting the SVFs in the Pre-processor or choose "
                                                                   "another file ")
                    return

                svfsizex = svf.shape[0]
                svfsizey = svf.shape[1]

                if not (svfsizex == sizex) & (svfsizey == sizey):  # &
                    QMessageBox.critical(self.dlg, "Error in vegetation canopy DSM",
                                         "All grids must be of same extent and resolution")
                    return

                tmp = svf + svfveg - 1.
                tmp[tmp < 0.] = 0.
                # %matlab crazyness around 0
                svfalfa = np.arcsin(np.exp((np.log((1. - tmp)) / 2.)))

            # Wall height and aspect #
            self.wallheight = self.layerComboManagerWH.getLayer()

            if self.wallheight is None:
                QMessageBox.critical(self.dlg, "Error", "No valid wall height grid is selected")
                return

            gdal.AllRegister()
            provider = self.wallheight.dataProvider()
            filePathOld = str(provider.dataSourceUri())
            dataSet = gdal.Open(filePathOld)
            self.wallheight = dataSet.ReadAsArray().astype(np.float)

            wallheightsizex = self.wallheight.shape[0]
            wallheightsizey = self.wallheight.shape[1]

            if not (wallheightsizex == sizex) & (wallheightsizey == sizey):
                QMessageBox.critical(self.dlg, "Error in wall height grid",
                                     "All grids must be of same extent and resolution")
                return

            self.wallaspect = self.layerComboManagerWA.getLayer()

            if self.wallaspect is None:
                QMessageBox.critical(self.dlg, "Error", "No valid wall aspect grid is selected")
                return

            gdal.AllRegister()
            provider = self.wallaspect.dataProvider()
            filePathOld = str(provider.dataSourceUri())
            dataSet = gdal.Open(filePathOld)
            self.wallaspect = dataSet.ReadAsArray().astype(np.float)

            wallaspectsizex = self.wallaspect.shape[0]
            wallaspectsizey = self.wallaspect.shape[1]

            if not (wallaspectsizex == sizex) & (wallaspectsizey == sizey):
                QMessageBox.critical(self.dlg, "Error in wall aspect grid",
                                     "All grids must be of same extent and resolution")
                return

            # Meteorological data #
            Twater = []
            if self.dlg.CheckBoxMetData.isChecked():
                self.read_metdata()
            else:
                self.metdata = np.zeros((1, 24)) - 999.

                date = self.dlg.calendarWidget.selectedDate()
                year = date.year()
                month = date.month()
                day = date.day()
                time = self.dlg.spinBoxTimeEdit.time()
                hour = time.hour()
                minu = time.minute()
                doy = self.day_of_year(year, month, day)

                Ta = self.dlg.doubleSpinBoxTa.value()
                RH = self.dlg.doubleSpinBoxRH.value()
                radG = self.dlg.doubleSpinBoxradG.value()
                radD = self.dlg.doubleSpinBoxradD.value()
                radI = self.dlg.doubleSpinBoxradI.value()
                Twater = self.dlg.doubleSpinBoxTwater.value()

                self.metdata[0, 0] = year
                self.metdata[0, 1] = doy
                self.metdata[0, 2] = hour
                self.metdata[0, 3] = minu
                self.metdata[0, 11] = Ta
                self.metdata[0, 10] = RH
                self.metdata[0, 14] = radG
                self.metdata[0, 21] = radD
                self.metdata[0, 22] = radI

            # Other parameters #
            absK = self.dlg.doubleSpinBoxShortwaveHuman.value()
            absL = self.dlg.doubleSpinBoxLongwaveHuman.value()
            pos = self.dlg.comboBox_posture.currentIndex()
            if pos == 0:
                Fside = 0.22
                Fup = 0.06
                height = 1.1
            else:
                Fside = 0.166666
                Fup = 0.166666
                height = 0.75
            albedo_b = self.dlg.doubleSpinBoxAlbedo_w.value()
            albedo_g = self.dlg.doubleSpinBoxAlbedo_g.value()
            ewall = self.dlg.doubleSpinBoxEmis_w.value()
            eground = self.dlg.doubleSpinBoxEmis_g.value()

            if self.dlg.CheckBoxElvis.isChecked():
                elvis = 1
            else:
                elvis = 0

            if self.dlg.CheckBoxBox.isChecked():
                cyl = 1
            else:
                cyl = 0

            # %Initialization of maps
            Knight = np.zeros((rows, cols))
            Tgmap1 = np.zeros((rows, cols))
            Tgmap1E = np.zeros((rows, cols))
            Tgmap1S = np.zeros((rows, cols))
            Tgmap1W = np.zeros((rows, cols))
            Tgmap1N = np.zeros((rows, cols))

            # building grid and land cover preparation
            sitein = self.plugin_dir + "/landcoverclasses_2016a.txt"
            f = open(sitein)
            lin = f.readlines()
            lc_class = np.zeros((lin.__len__() - 1, 6))
            for i in range(1, lin.__len__()):
                lines = lin[i].split()
                for j in np.arange(1, 7):
                    lc_class[i - 1, j - 1] = float(lines[j])

            if self.dlg.checkBoxDEM.isChecked():
                buildings = np.copy(self.lcgrid)
                buildings[buildings == 7] = 1
                buildings[buildings == 6] = 1
                buildings[buildings == 5] = 1
                buildings[buildings == 4] = 1
                buildings[buildings == 3] = 1
                buildings[buildings == 2] = 0
            else:
                buildings = self.dsm - self.dem
                buildings[buildings < 2.] = 1.
                buildings[buildings >= 2.] = 0.
                #np.where(np.transpose(self.dsm - self.dem) < 2.)

            if self.dlg.checkBoxBuild.isChecked():
                self.saveraster(self.gdal_dsm, self.folderPath[0] + '/buildings.tif', buildings)

            if self.dlg.checkBoxUseOnlyGlobal.isChecked():
                onlyglobal = 1
            else:
                onlyglobal = 0

            location = {'longitude': lon, 'latitude': lat, 'altitude': alt}
            YYYY, altitude, azimuth, zen, jday, leafon, dectime, altmax = \
                metload.Solweig_2015a_metdata_noload(self.metdata, location, UTC)

            # %Creating vectors from meteorological input
            DOY = self.metdata[:, 1]
            hours = self.metdata[:, 2]
            minu = self.metdata[:, 3]
            Ta = self.metdata[:, 11]
            RH = self.metdata[:, 10]
            radG = self.metdata[:, 14]
            radD = self.metdata[:, 21]
            radI = self.metdata[:, 22]
            P = self.metdata[:, 12]
            Ws = self.metdata[:, 9]
            # %Wd=met(:,13);

            # POIs check
            if self.dlg.checkboxUsePOI.isChecked():
                header = 'yyyy id   it imin dectime altitude azimuth kdir kdiff kglobal kdown   kup    keast ksouth ' \
                         'kwest knorth ldown   lup    least lsouth lwest  lnorth   Ta      Tg     RH    Esky   Tmrt    ' \
                         'I0     CI   Shadow  SVF_b  SVF_bv KsideI'

                poilyr = self.layerComboManagerPOI.getLayer()
                if poilyr is None:
                    QMessageBox.critical(self.dlg, "Error", "No valid point layer is selected")
                    return

                poi_field = self.layerComboManagerPOIfield.getFieldName()
                if poi_field is None:
                    QMessageBox.critical(self.dlg, "Error", "An attribute with unique values must be selected")
                    return
                vlayer = QgsVectorLayer(poilyr.source(), "point", "ogr")
                prov = vlayer.dataProvider()
                #fields = prov.fields()
                idx = vlayer.fieldNameIndex(poi_field)
                numfeat = vlayer.featureCount()
                self.poiname = []
                self.poisxy = np.zeros((numfeat, 3)) - 999
                ind = 0
                for f in vlayer.getFeatures():  # looping through each grid polygon
                    y = f.geometry().centroid().asPoint().y()
                    x = f.geometry().centroid().asPoint().x()

                    self.poiname.append(f.attributes()[idx])

                    #self.poisxy[ind, 0] = f.attributes()[idx]
                    self.poisxy[ind, 0] = ind
                    self.poisxy[ind, 1] = np.round(x - minx)
                    self.poisxy[ind, 2] = np.round(miny + rows - y)
                    #attributes = f.attributes()
                    ind += 1

                uni = set(self.poiname)
                #self.iface.messageBar().pushMessage("test", str(uni))
                #self.iface.messageBar().pushMessage("test2", str(poisxy.shape[0]))
                if not uni.__len__() == self.poisxy.shape[0]:
                    QMessageBox.critical(self.dlg, "Error", "A POI attribute with unique values must be selected")
                    return

                for k in range(0, self.poisxy.shape[0]):
                    poi_save = [] # np.zeros((1, 33))
                    #data_out = self.folderPath[0] + '/POI_' + str(self.poisxy[k, 0]) + '.txt'
                    data_out = self.folderPath[0] + '/POI_' + str(self.poiname[k]) + '.txt'
                    np.savetxt(data_out, poi_save,  delimiter=' ', header=header, comments='')  # fmt=numformat,
                    #f_handle = file(data_out, 'a')
                    #endoffile = [-9, -9]
                    #np.savetxt(f_handle, endoffile, fmt='%2d')
                    #f_handle.close()

            self.dlg.progressBar.setRange(0, Ta.__len__())

            # %Parameterisarion for Lup
            if not height:
                height = 1.1

            # %Radiative surface influence, Rule of thumb by Schmid et al. (1990).
            first = np.round(height)
            if first == 0.:
                first = 1.
            second = np.round((height * 20.))

            if self.usevegdem == 1:
                # % Vegetation transmittivity of shortwave radiation
                psi = leafon * self.trans
                psi[leafon == 0] = 0.5
                # amaxvalue
                vegmax = self.vegdsm.max()
                amaxvalue = self.dsm.max() - self.dsm.min()
                amaxvalue = np.maximum(amaxvalue, vegmax)

                # Elevation vegdsms if buildingDEM includes ground heights
                vegdem = self.vegdsm + self.dsm
                vegdem[vegdem == self.dsm] = 0
                vegdem2 = self.vegdsm2 + self.dsm
                vegdem2[vegdem2 == self.dsm] = 0

                # % Bush separation
                bush = np.logical_not((vegdem2 * vegdem)) * vegdem

                svfbuveg = (svf - (1. - svfveg) * (1. - self.trans))  # % major bug fixed 20141203
            else:
                psi = leafon * 0. + 1.
                svfbuveg = svf
                bush = np.zeros([rows, cols])
                amaxvalue = 0

            # QMessageBox.critical(None, "Test", str(amaxvalue))
            # return

            # % Ts parameterisation maps
            if self.landcover == 1.:
                [TgK, Tstart, alb_grid, emis_grid, TgK_wall, Tstart_wall, TmaxLST, TmaxLST_wall] = \
                    Tgmaps_v1(self.lcgrid, lc_class)
            else:
                TgK = Knight + 0.37
                Tstart = Knight - 3.41
                alb_grid = Knight + albedo_g
                emis_grid = Knight + eground
                TgK_wall = 0.37
                Tstart_wall = -3.41
                TmaxLST = 15.
                TmaxLST_wall = 15.

            # Initialisation of time related variables
            if Ta.__len__() == 1:
                timestepdec = 0
            else:
                timestepdec = dectime[1] - dectime[0]
            timeadd = 0.
            timeaddE = 0.
            timeaddS = 0.
            timeaddW = 0.
            timeaddN = 0.
            firstdaytime = 1.

            # self.iface.messageBar().pushMessage("Ta.__len__  ", str(int(Ta.__len__())))
            #self.iface.messageBar().pushMessage("__len__", str(buildings.shape[0]))
            #self.iface.messageBar().pushMessage("__len__", str(self.lcgrid.shape[0]))

            #  If metfile starts at night
            CI = 1.
            # self.iface.messageBar().pushMessage("Ta", self.folderPath[0] + '/Tmrt_' + str(int(YYYY[0, i])) + '_' + str(int(DOY[0, i])) + '_' + str(int(hours[0, i])) + str(int(minu[0, i])) + '.tif')
            # self.iface.messageBar().pushMessage("hour", str(hours[5]))
            self.startWorker(self.dsm, self.scale, rows, cols, svf, svfN, svfW, svfE, svfS, svfveg,
                        svfNveg, svfEveg, svfSveg, svfWveg, svfaveg, svfEaveg, svfSaveg, svfWaveg, svfNaveg,
                        self.vegdsm, self.vegdsm2, albedo_b, absK, absL, ewall, Fside, Fup, altitude,
                        azimuth, zen, jday, self.usevegdem, onlyglobal, buildings, location,
                        psi, self.landcover, self.lcgrid, dectime, altmax, self.wallaspect,
                        self.wallheight, cyl, elvis, Ta, RH, radG, radD, radI, P, amaxvalue,
                        bush, Twater, TgK, Tstart, alb_grid, emis_grid, TgK_wall, Tstart_wall, TmaxLST,
                        TmaxLST_wall, first, second, svfalfa, svfbuveg, firstdaytime, timeadd, timeaddE, timeaddS,
                        timeaddW, timeaddN, timestepdec, Tgmap1, Tgmap1E, Tgmap1S, Tgmap1W, Tgmap1N, CI, self.dlg,
                        YYYY, DOY, hours, minu, self.gdal_dsm, self.folderPath, self.poisxy, self.poiname)

            # # Main calcualtions
            # # Loop through time series
            # tmrtplot = np.zeros((rows, cols))
            # for i in np.arange(0, Ta.__len__()):
            #     # Daily water body temperature
            #     if self.landcover == 1:
            #         if ((dectime[i] - np.floor(dectime[i]))) == 0 or (i == 0):
            #             Twater = np.mean(Ta[jday[0] == np.floor(dectime[i])])
            #
            #     # Nocturnal cloudfraction from Offerle et al. 2003
            #     if (dectime[i] - np.floor(dectime[i])) == 0:
            #         alt = altitude[i:altitude.__len__()]
            #         alt2 = np.where(alt > 1)
            #         rise = alt2[1][0]
            #         [_, CI, _, _, _] = clearnessindex_2013b(zen[0, i + rise + 1], jday[0, i + rise + 1],
            #                                                 Ta[i + rise + 1],
            #                                                 RH[i + rise + 1] / 100., radG[i + rise + 1], location,
            #                                                 P[i + rise + 1])  # i+rise+1 to match matlab code. correct?
            #         if (CI > 1) or (CI == np.inf):
            #             CI = 1
            #     # self.iface.messageBar().pushMessage("__len__", str(Ta.__len__()))
            #     # self.iface.messageBar().pushMessage("len", str(len(Ta)))
            #     # self.iface.messageBar().pushMessage("Test", str(Ta.__len__()))
            #     Tmrt, Kdown, Kup, Ldown, Lup, Tg, ea, esky, I0, CI, shadow, firstdaytime, timestepdec, timeadd, \
            #     Tgmap1, timeaddE, Tgmap1E, timeaddS, Tgmap1S, timeaddW, Tgmap1W, timeaddN, Tgmap1N \
            #         = so.Solweig_2015a_calc(i, self.dsm, self.scale, rows, cols, svf, svfN, svfW, svfE, svfS, svfveg,
            #             svfNveg, svfEveg, svfSveg, svfWveg, svfaveg, svfEaveg, svfSaveg, svfWaveg, svfNaveg,
            #             self.vegdsm, self.vegdsm2, albedo_b, absK, absL, ewall, Fside, Fup, altitude[0][i],
            #             azimuth[0][i], zen[0][i], jday[0][i], self.usevegdem, onlyglobal, buildings, location,
            #             psi[0][i], self.landcover, self.lcgrid, dectime[i], altmax[0][i], self.wallaspect,
            #             self.wallheight, cyl, elvis, Ta[i], RH[i], radG[i], radD[i], radI[i], P[i], amaxvalue,
            #             bush, Twater, TgK, Tstart, alb_grid, emis_grid, TgK_wall, Tstart_wall, TmaxLST,
            #             TmaxLST_wall, first, second, svfalfa, svfbuveg, firstdaytime, timeadd, timeaddE, timeaddS,
            #             timeaddW, timeaddN, timestepdec, Tgmap1, Tgmap1E, Tgmap1S, Tgmap1W, Tgmap1N, CI)
            #
            #     tmrtplot = tmrtplot + Tmrt
            #     # self.iface.messageBar().pushMessage("__len__", str(int(YYYY[0, i])))
            #     if self.dlg.CheckBoxTmrt.isChecked():
            #self.saveraster(self.gdal_dsm, self.folderPath[0] + '/buildings.tif', buildings)
            #     if self.dlg.CheckBoxKup.isChecked():
            #         self.saveraster(self.gdal_dsm, self.folderPath[0] + '/Kup_' + str(int(YYYY[0, i])) + '_' + str(int(DOY[i]))
            #                         + '_' + str(int(hours[i])) + str(int(minu[i])) + '.tif', Kup)
            #     if self.dlg.CheckBoxKdown.isChecked():
            #         self.saveraster(self.gdal_dsm, self.folderPath[0] + '/Kdown_' + str(int(YYYY[0, i])) + '_' + str(int(DOY[i]))
            #                         + '_' + str(int(hours[i])) + str(int(minu[i])) + '.tif', Kdown)
            #     if self.dlg.CheckBoxLup.isChecked():
            #         self.saveraster(self.gdal_dsm, self.folderPath[0] + '/Lup_' + str(int(YYYY[0, i])) + '_' + str(int(DOY[i]))
            #                         + '_' + str(int(hours[i])) + str(int(minu[i])) + '.tif', Lup)
            #     if self.dlg.CheckBoxLdown.isChecked():
            #         self.saveraster(self.gdal_dsm, self.folderPath[0] + '/Ldown_' + str(int(YYYY[0, i])) + '_' + str(int(DOY[i]))
            #                         + '_' + str(int(hours[i])) + str(int(minu[i])) + '.tif', Ldown)
            #     if self.dlg.CheckBoxShadow.isChecked():
            #         self.saveraster(self.gdal_dsm, self.folderPath[0] + '/Shadow_' + str(int(YYYY[0, i])) + '_' + str(int(DOY[i]))
            #                         + '_' + str(int(hours[i])) + str(int(minu[i])) + '.tif', shadow)
            #
            # if self.dlg.CheckBoxTmrt.isChecked():
            #     tmrtplot = tmrtplot / Ta.__len__()
            #     self.saveraster(self.gdal_dsm, self.folderPath[0] + '/Tmrt_average.tif', tmrtplot)
            #
            # # load result into canvas
            # if self.dlg.checkBoxIntoCanvas.isChecked():
            #     rlayer = self.iface.addRasterLayer(self.folderPath[0] + '/Tmrt_average.tif')
            #
            #     # Set opacity
            #     # rlayer.renderer().setOpacity(0.5)
            #
            #     # Trigger a repaint
            #     if hasattr(rlayer, "setCacheImage"):
            #         rlayer.setCacheImage(None)
            #     rlayer.triggerRepaint()
            #
            # self.iface.messageBar().pushMessage("SOLWEIG", "Model calculations successful.")

    def run(self):
        """This methods is needed for QGIS to start the plugin"""
        self.dlg.show()
        self.dlg.exec_()

    def help(self):
        url = 'http://urban-climate.net/umep/UMEP_Manual#Outdoor_Thermal_Comfort:_SOLWEIG'
        webbrowser.open_new_tab(url)

    def saveraster(self, gdal_data, filename, raster):
        rows = gdal_data.RasterYSize
        cols = gdal_data.RasterXSize

        outDs = gdal.GetDriverByName("GTiff").Create(filename, cols, rows, int(1), GDT_Float32)
        outBand = outDs.GetRasterBand(1)

        # write the data
        outBand.WriteArray(raster, 0, 0)
        # flush data to disk, set the NoData value and calculate stats
        outBand.FlushCache()
        outBand.SetNoDataValue(-9999)

        # georeference the image and set the projection
        outDs.SetGeoTransform(gdal_data.GetGeoTransform())
        outDs.SetProjection(gdal_data.GetProjection())

    def startWorker(self, dsm, scale, rows, cols, svf, svfN, svfW, svfE, svfS, svfveg,
                        svfNveg, svfEveg, svfSveg, svfWveg, svfaveg, svfEaveg, svfSaveg, svfWaveg, svfNaveg,
                        vegdsm, vegdsm2, albedo_b, absK, absL, ewall, Fside, Fup, altitude,
                        azimuth, zen, jday, usevegdem, onlyglobal, buildings, location,
                        psi, landcover, lcgrid, dectime, altmax, wallaspect,
                        wallheight, cyl, elvis, Ta, RH, radG, radD, radI, P, amaxvalue,
                        bush, Twater, TgK, Tstart, alb_grid, emis_grid, TgK_wall, Tstart_wall, TmaxLST,
                        TmaxLST_wall, first, second, svfalfa, svfbuveg, firstdaytime, timeadd, timeaddE, timeaddS,
                        timeaddW, timeaddN, timestepdec, Tgmap1, Tgmap1E, Tgmap1S, Tgmap1W, Tgmap1N, CI, dlg,
                        YYYY, DOY, hours, minu, gdal_dsm, folderPath, poisxy, poiname):

        # create a new worker instance
        worker = Worker(dsm, scale, rows, cols, svf, svfN, svfW, svfE, svfS, svfveg,
                        svfNveg, svfEveg, svfSveg, svfWveg, svfaveg, svfEaveg, svfSaveg, svfWaveg, svfNaveg,
                        vegdsm, vegdsm2, albedo_b, absK, absL, ewall, Fside, Fup, altitude,
                        azimuth, zen, jday, usevegdem, onlyglobal, buildings, location,
                        psi, landcover, lcgrid, dectime, altmax, wallaspect,
                        wallheight, cyl, elvis, Ta, RH, radG, radD, radI, P, amaxvalue,
                        bush, Twater, TgK, Tstart, alb_grid, emis_grid, TgK_wall, Tstart_wall, TmaxLST,
                        TmaxLST_wall, first, second, svfalfa, svfbuveg, firstdaytime, timeadd, timeaddE, timeaddS,
                        timeaddW, timeaddN, timestepdec, Tgmap1, Tgmap1E, Tgmap1S, Tgmap1W, Tgmap1N, CI, dlg,
                        YYYY, DOY, hours, minu, gdal_dsm, folderPath, poisxy, poiname)

        self.dlg.runButton.setText('Cancel')
        self.dlg.runButton.clicked.disconnect()
        self.dlg.runButton.clicked.connect(worker.kill)
        self.dlg.pushButtonClose.setEnabled(False)

        # start the worker in a new thread
        thread = QThread(self.dlg)
        worker.moveToThread(thread)
        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        worker.progress.connect(self.progress_update)
        thread.started.connect(worker.run)
        thread.start()
        self.thread = thread
        self.worker = worker

    def workerFinished(self, ret):
        # clean up the worker and thread
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()
        # remove widget from message bar
        if ret is not None:
            # report the result
            # load result into canvas
            if self.dlg.checkBoxIntoCanvas.isChecked():
                tmrtplot = ret["tmrtplot"]
                self.saveraster(self.gdal_dsm, self.folderPath[0] + '/Tmrt_average.tif', tmrtplot)
                rlayer = self.iface.addRasterLayer(self.folderPath[0] + '/Tmrt_average.tif', 'Average Tmrt [degC]')

                # Trigger a repaint
                if hasattr(rlayer, "setCacheImage"):
                    rlayer.setCacheImage(None)
                rlayer.triggerRepaint()

                rlayer.loadNamedStyle(self.plugin_dir + '/tmrt.qml')
                # self.QgsMapLayerRegistry.instance().addMapLayer(rlayer)

                if hasattr(rlayer, "setCacheImage"):
                    rlayer.setCacheImage(None)
                rlayer.triggerRepaint()

                # Set opacity
                # rlayer.renderer().setOpacity(0.5)

                # Trigger a repaint
                # if hasattr(rlayer, "setCacheImage"):
                #     rlayer.setCacheImage(None)
                # rlayer.triggerRepaint()

            self.iface.messageBar().pushMessage("SOLWEIG", "Model calculations successful.")
            #
            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.pushButtonClose.setEnabled(True)
        else:
            # notify the user that something went wrong
            self.iface.messageBar().pushMessage(
                'Operations cancelled either by user or error. See the General tab in Log Meassages Panel (speech bubble, lower right) for more information.',
                level=QgsMessageBar.CRITICAL, duration=3)
            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.pushButtonClose.setEnabled(True)
            self.dlg.progressBar.setValue(0)

    def workerError(self, errorstring):
        QgsMessageLog.logMessage(errorstring, level=QgsMessageLog.CRITICAL)