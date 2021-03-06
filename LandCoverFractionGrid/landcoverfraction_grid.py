# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LandCoverFractionGrid
                                 A QGIS plugin
 Calculates fraction of land cover types on a vector grid
                              -------------------
        begin                : 2015-07-09
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Fredrik Lindberg
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
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import object
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QThread, QCoreApplication
from qgis.PyQt.QtWidgets import QFileDialog, QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import *
from qgis.gui import *
import os
from osgeo import gdal
from .landcoverfraction_grid_dialog import LandCoverFractionGridDialog
import os.path
from .lcfracworker import Worker
import webbrowser

# Initialize Qt resources from file resources.py
# from . import resources_rc

class LandCoverFractionGrid(object):
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
            'LandCoverFractionGrid_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = LandCoverFractionGridDialog()
        self.dlg.runButton.clicked.connect(self.start_progress)
        self.dlg.pushButtonSave.clicked.connect(self.folder_path)
        self.dlg.helpButton.clicked.connect(self.help)
        self.dlg.progressBar.setValue(0)

        self.fileDialog = QFileDialog()
        # self.fileDialog.setFileMode(4)
        # self.fileDialog.setAcceptMode(1)  # Save
        self.fileDialog.setFileMode(QFileDialog.Directory)
        self.fileDialog.setOption(QFileDialog.ShowDirsOnly, True)

        for i in range(1, 25):
            if 360 % i == 0:
                self.dlg.degreeBox.addItem(str(i))
        self.dlg.degreeBox.setCurrentIndex(4)

        self.folderPath = 'None'
        self.degree = 5.0
        self.dsm = None
        self.dem = None
        self.scale = None
        self.steps = 0

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Land Cover Fraction Grid')
        # self.toolbar = self.iface.addToolBar(u'LandCoverFractionGrid')
        # self.toolbar.setObjectName(u'LandCoverFractionGrid')

        # self.layerComboManagerPolygrid = VectorLayerCombo(self.dlg.comboBox_Polygrid)
        # fieldgen = VectorLayerCombo(self.dlg.comboBox_Polygrid, initLayer="", options={"geomType": QGis.Polygon})
        self.layerComboManagerPolygrid = QgsMapLayerComboBox(self.dlg.widget_Polygrid)
        self.layerComboManagerPolygrid.setCurrentIndex(-1)
        self.layerComboManagerPolygrid.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.layerComboManagerPolygrid.setFixedWidth(175)
        self.layerComboManagerPolyField = QgsFieldComboBox(self.dlg.widget_Field)
        self.layerComboManagerPolyField.setFilters(QgsFieldProxyModel.Numeric)
        self.layerComboManagerPolygrid.layerChanged.connect(self.layerComboManagerPolyField.setLayer)
        # self.layerComboManagerPolyField = FieldCombo(self.dlg.comboBox_Field, fieldgen) #, options={"fieldType":QGis.Float32}

        # self.layerComboManagerLCgrid = RasterLayerCombo(self.dlg.comboBox_lcgrid)
        # RasterLayerCombo(self.dlg.comboBox_lcgrid, initLayer="")
        self.layerComboManagerLCgrid = QgsMapLayerComboBox(self.dlg.widget_lcgrid)
        self.layerComboManagerLCgrid.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.layerComboManagerLCgrid.setFixedWidth(175)
        self.layerComboManagerLCgrid.setCurrentIndex(-1)



        if not (os.path.isdir(self.plugin_dir + '/data')):
            os.mkdir(self.plugin_dir + '/data')

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('LandCoverFractionGrid', message)

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

        icon_path = ':/plugins/LandCoverFractionGrid/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Calculates fraction of land cover types on a vector grid'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Land Cover Fraction Grid'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def folder_path(self):
        self.fileDialog.open()
        result = self.fileDialog.exec_()
        if result == 1:
            self.folderPath = self.fileDialog.selectedFiles()
            self.dlg.textOutput.setText(self.folderPath[0])

    def start_progress(self):
        self.steps = 0
        poly = self.layerComboManagerPolygrid.currentLayer()
        if poly is None:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return
        if not poly.geometryType() == 2:
            QMessageBox.critical(None, "Error", "No valid Polygon layer is selected")
            return

        poly_field = self.layerComboManagerPolyField.currentField()
        if poly_field == '':
            QMessageBox.critical(None, "Error", "An attribute with unique fields/records must be selected")
            return

        vlayer = QgsVectorLayer(poly.source(), "polygon", "ogr")
        prov = vlayer.dataProvider()
        fields = prov.fields()
        # idx = vlayer.fieldNameIndex(poly_field)
        idx = vlayer.fields().indexFromName(poly_field)

        typetest = fields.at(idx).type()
        if typetest == 10:
            QMessageBox.critical(None, "ID field is sting type", "ID field must be either integer or float")
            return

        dir_poly = self.plugin_dir + '/data/poly_temp.shp'
        self.dlg.progressBar.setMaximum(vlayer.featureCount())

        lc_grid = self.layerComboManagerLCgrid.currentLayer()
        if lc_grid is None:
            QMessageBox.critical(None, "Error", "No valid raster layer is selected")
            return

        if self.dlg.radioButtonExtent.isChecked():  # What search method to use
            imid = 0
        else:
            imid = 1

        if self.folderPath == 'None':
            QMessageBox.critical(None, "Error", "Select a valid output folder")
            return

        radius = self.dlg.spinBoxDistance.value()
        degree = float(self.dlg.degreeBox.currentText())

        # self.iface.messageBar().pushMessage("test: ", str(test))

        self.startWorker(lc_grid, poly, poly_field, vlayer, prov, fields, idx, dir_poly, self.iface,
                         self.plugin_dir, self.folderPath, self.dlg, imid, radius, degree)

    def startWorker(self, lc_grid, poly, poly_field, vlayer, prov, fields, idx, dir_poly, iface, plugin_dir,
                    folderPath, dlg, imid, radius, degree):

        worker = Worker(lc_grid, poly, poly_field, vlayer, prov, fields, idx, dir_poly, iface,
                        plugin_dir, folderPath, dlg, imid, radius, degree)

        self.dlg.runButton.setText('Cancel')
        self.dlg.runButton.clicked.disconnect()
        self.dlg.runButton.clicked.connect(worker.kill)
        self.dlg.closeButton.setEnabled(False)

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
        try:
            self.worker.deleteLater()
        except RuntimeError:
             pass
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()

        if ret == 1:
            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.closeButton.setEnabled(True)
            self.dlg.progressBar.setValue(0)
            # QMessageBox.information(None, "Image Morphometric Parameters",
            #                         "Process finished! Check General Messages (speech bubble, lower left) "
            #                         "to obtain information of the process.")
            self.iface.messageBar().pushMessage("Land Cover Fraction Grid",
                                    "Process finished! Check General Messages (speech bubble, lower left) "
                                    "to obtain information of the process.", duration=5)
        else:
            self.dlg.runButton.setText('Run')
            self.dlg.runButton.clicked.disconnect()
            self.dlg.runButton.clicked.connect(self.start_progress)
            self.dlg.closeButton.setEnabled(True)
            self.dlg.progressBar.setValue(0)
            QMessageBox.information(None, "Land Cover Fraction Grid", "Operations cancelled, "
                                                                           "process unsuccessful! See the General tab in Log Meassages Panel (speech bubble, lower right) for more information.")

    def workerError(self, errorstring):
        QgsMessageLog.logMessage(errorstring, level=Qgis.Critical)

    def progress_update(self):
        self.steps += 1
        self.dlg.progressBar.setValue(self.steps)

    def run(self):
        try:
            import scipy
        except Exception as e:
            QMessageBox.critical(None, 'Error', 'This plugin requires the scipy package '
                                                'to be installed. Please consult the FAQ in the manual for further '
                                                'information on how to install missing python packages.')
            return
        # try:
        #     import skimage
        # except Exception as e:
        #     QMessageBox.critical(None, 'Error', 'This plugin requires the scikit-image package '
        #                                         'to be installed. Please consult the FAQ in the manual for further '
        #                                         'information on how to install missing python packages.')
        #     return
        self.dlg.show()
        self.dlg.exec_()
        gdal.UseExceptions()
        gdal.AllRegister()

    def help(self):
        url = 'https://umep-docs.readthedocs.io/en/latest/pre-processor/Urban%20Land%20Cover%20Land%20Cover%20Fraction%20(Grid).html'
        webbrowser.open_new_tab(url)
