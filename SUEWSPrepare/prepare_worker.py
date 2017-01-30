from PyQt4 import QtCore
from PyQt4.QtCore import QVariant
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QFileDialog
from qgis.core import *  # QgsVectorLayer, QgsVectorFileWriter, QgsFeature, QgsRasterLayer, QgsGeometry, QgsMessageLog
import traceback
import numpy as np
from osgeo import gdal, osr
# import subprocess
import sys
import linecache
import os
# import fileinput
# import time
from shutil import copyfile
from ..Utilities import f90nml

class Worker(QtCore.QObject):

    finished = QtCore.pyqtSignal(bool)
    error = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal()

    def __init__(self, vlayer, nbr_header, poly_field, Metfile_path, start_DLS, end_DLS, LCF_from_file, LCFfile_path, LCF_Paved,
                 LCF_buildings, LCF_evergreen, LCF_decidious, LCF_grass, LCF_baresoil, LCF_water, IMP_from_file, IMPfile_path,
                 IMP_heights_mean, IMP_z0, IMP_zd, IMP_fai, IMPveg_from_file, IMPvegfile_path, IMPveg_heights_mean_eve,
                 IMPveg_heights_mean_dec, IMPveg_fai_eve, IMPveg_fai_dec, pop_density, widget_list, wall_area,
                 land_use_from_file, land_use_file_path, lines_to_write, plugin_dir, output_file_list, map_units, header_sheet, wall_area_info, output_dir,
                 day_since_rain, leaf_cycle, soil_moisture, file_code):

        QtCore.QObject.__init__(self)
        self.killed = False
        self.vlayer = vlayer
        self.nbr_header = nbr_header
        self.poly_field = poly_field
        self.Metfile_path = Metfile_path
        self.start_DLS = start_DLS
        self.end_DLS = end_DLS
        self.LCF_from_file = LCF_from_file
        self.LCFfile_path = LCFfile_path
        self.LCF_Paved = LCF_Paved
        self.LCF_buildings = LCF_buildings
        self.LCF_evergreen = LCF_evergreen
        self.LCF_decidious = LCF_decidious
        self.LCF_grass = LCF_grass
        self.LCF_baresoil = LCF_baresoil
        self.LCF_water = LCF_water
        self.IMP_from_file = IMP_from_file
        self.IMPfile_path = IMPfile_path
        self.IMP_heights_mean = IMP_heights_mean
        self.IMP_z0 = IMP_z0
        self.IMP_zd = IMP_zd
        self.IMP_fai = IMP_fai
        self.IMPveg_from_file = IMPveg_from_file
        self.IMPvegfile_path = IMPvegfile_path
        self.IMPveg_heights_mean_eve = IMPveg_heights_mean_eve
        self.IMPveg_heights_mean_dec = IMPveg_heights_mean_dec
        self.IMPveg_fai_eve = IMPveg_fai_eve
        self.IMPveg_fai_dec = IMPveg_fai_dec
        self.pop_density = pop_density
        self.widget_list = widget_list
        self.wall_area = wall_area
        self.land_use_from_file = land_use_from_file
        self.land_use_file_path = land_use_file_path
        self.lines_to_write = lines_to_write
        self.output_dir = output_dir
        self.output_file_list = output_file_list
        self.map_units = map_units
        self.header_sheet = header_sheet
        self.wall_area_info = wall_area_info
        self.input_path = plugin_dir + '/Input/'
        self.output_path = plugin_dir + '/Output/'
        self.plugin_dir = plugin_dir
        self.day_since_rain = day_since_rain
        self.leaf_cycle = leaf_cycle
        self.soil_moisture = soil_moisture
        self.file_code = file_code

    def run(self):
        try:
            for feature in self.vlayer.getFeatures():
                if self.killed is True:
                    break
                new_line = [None] * len(self.nbr_header)
                print_line = True
                feat_id = int(feature.attribute(self.poly_field))
                code = "Grid"
                index = self.find_index(code)
                new_line[index] = str(feat_id)

                year = None
                year2 = None

                if self.Metfile_path is None:
                    QMessageBox.critical(None, "Error", "Meteorological data file has not been provided,"
                                                        " please check the main tab")
                    return
                elif os.path.isfile(self.Metfile_path):
                    with open(self.Metfile_path) as file:
                        next(file)
                        for line in file:
                            split = line.split()
                            if year == split[0]:
                                break
                            else:
                                if year2 == split[0]:
                                    year = split[0]
                                    break
                                elif year is None:
                                    year = split[0]
                                else:
                                    year2 = split[0]

                else:
                    QMessageBox.critical(None, "Error",
                                         "Could not find the file containing meteorological data")
                    return

                code = "Year"
                index = self.find_index(code)
                new_line[index] = str(year)
                code = "StartDLS"
                index = self.find_index(code)
                new_line[index] = str(self.start_DLS)
                code = "EndDLS"
                index = self.find_index(code)
                new_line[index] = str(self.end_DLS)

                old_cs = osr.SpatialReference()
                vlayer_ref = self.vlayer.crs().toWkt()
                old_cs.ImportFromWkt(vlayer_ref)

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

                # area_wkt = """
                # GEOCCS["WGS 84 (geocentric)",
                #     DATUM["World Geodetic System 1984",
                #         SPHEROID["WGS 84",6378137.0,298.257223563,
                #             AUTHORITY["EPSG","7030"]],
                #         AUTHORITY["EPSG","6326"]],
                #     PRIMEM["Greenwich",0.0,
                #         AUTHORITY["EPSG","8901"]],
                #     UNIT["m",1.0],
                #     AXIS["Geocentric X",OTHER],
                #     AXIS["Geocentric Y",EAST],
                #     AXIS["Geocentric Z",NORTH],
                #     AUTHORITY["EPSG","4328"]]"""

                # new_cs_area = QgsCoordinateReferenceSystem(area_wkt)

                transform = osr.CoordinateTransformation(old_cs, new_cs)

                centroid = feature.geometry().centroid().asPoint()
                # areatransform = QgsCoordinateTransform(old_cs_area, new_cs_area)
                # feature.geometry().transform(areatransform)
                area = feature.geometry().area()
                # map_units = self.vlayer.crs().mapUnits()
                #
                if self.map_units == 0:
                    hectare = area * 0.0001

                elif self.map_units == 1:
                    hectare = area / 107640.

                else:
                    hectare = area
                #
                # else:
                #     QMessageBox.critical(None, "Error",
                #                          "Could not identify the map units of the polygon layer coordinate "
                #                          "reference system")
                #     return

                lonlat = transform.TransformPoint(centroid.x(), centroid.y())
                code = "lat"
                index = self.find_index(code)
                new_line[index] = str(lonlat[1])
                code = "lng"
                index = self.find_index(code)
                new_line[index] = str(lonlat[0])
                code = "SurfaceArea"
                index = self.find_index(code)
                new_line[index] = str(hectare)

                altitude = 0
                day = 1
                hour = 0
                minute = 0

                code = "Alt"
                index = self.find_index(code)
                new_line[index] = str(altitude)
                code = "id"
                index = self.find_index(code)
                new_line[index] = str(day)
                code = "ih"
                index = self.find_index(code)
                new_line[index] = str(hour)
                code = "imin"
                index = self.find_index(code)
                new_line[index] = str(minute)

                if self.LCF_from_file:
                    found_LCF_line = False
                    # if os.path.isfile(self.LCFfile_path):
                    with open(self.LCFfile_path) as file:
                        next(file)
                        for line in file:
                            split = line.split()
                            if feat_id == int(split[0]):
                                LCF_paved = split[1]
                                LCF_buildings = split[2]
                                LCF_evergreen = split[3]
                                LCF_decidious = split[4]
                                LCF_grass = split[5]
                                LCF_baresoil = split[6]
                                LCF_water = split[7]
                                found_LCF_line = True
                                break
                        if not found_LCF_line:
                            LCF_paved = -999
                            LCF_buildings = -999
                            LCF_evergreen = -999
                            LCF_decidious = -999
                            LCF_grass = -999
                            LCF_baresoil = -999
                            LCF_water = -999
                            print_line = False
                    # else:
                    #     QMessageBox.critical(None, "Error",
                    #                          "Could not find the file containing land cover fractions")
                    #     return
                else:
                    LCF_paved = feature.attribute(self.LCF_Paved.getFieldName())
                    LCF_buildings = feature.attribute(self.LCF_Buildings.getFieldName())
                    LCF_evergreen = feature.attribute(self.LCF_Evergreen.getFieldName())
                    LCF_decidious = feature.attribute(self.LCF_Decidious.getFieldName())
                    LCF_grass = feature.attribute(self.LCF_Grass.getFieldName())
                    LCF_baresoil = feature.attribute(self.LCF_Baresoil.getFieldName())
                    LCF_water = feature.attribute(self.LCF_Water.getFieldName())

                code = "Fr_Paved"
                index = self.find_index(code)
                new_line[index] = str(LCF_paved)
                code = "Fr_Bldgs"
                index = self.find_index(code)
                new_line[index] = str(LCF_buildings)
                code = "Fr_EveTr"
                index = self.find_index(code)
                new_line[index] = str(LCF_evergreen)
                code = "Fr_DecTr"
                index = self.find_index(code)
                new_line[index] = str(LCF_decidious)
                code = "Fr_Grass"
                index = self.find_index(code)
                new_line[index] = str(LCF_grass)
                code = "Fr_Bsoil"
                index = self.find_index(code)
                new_line[index] = str(LCF_baresoil)
                code = "Fr_Water"
                index = self.find_index(code)
                new_line[index] = str(LCF_water)

                irrFr_EveTr = 0
                irrFr_DecTr = 0
                irrFr_Grass = 0

                code = "IrrFr_EveTr"
                index = self.find_index(code)
                new_line[index] = str(irrFr_EveTr)
                code = "IrrFr_DecTr"
                index = self.find_index(code)
                new_line[index] = str(irrFr_DecTr)
                code = "IrrFr_Grass"
                index = self.find_index(code)
                new_line[index] = str(irrFr_Grass)

                Traffic_Rate = 99999
                BuildEnergy_Use = 99999

                code = "TrafficRate"
                index = self.find_index(code)
                new_line[index] = str(Traffic_Rate)
                code = "BuildEnergyUse"
                index = self.find_index(code)
                new_line[index] = str(BuildEnergy_Use)

                Activity_ProfWD = 55663
                Activity_ProfWE = 55664

                code = "ActivityProfWD"
                index = self.find_index(code)
                new_line[index] = str(Activity_ProfWD)
                code = "ActivityProfWE"
                index = self.find_index(code)
                new_line[index] = str(Activity_ProfWE)

                if self.IMP_from_file:
                    found_IMP_line = False

                    # if self.IMPfile_path is None:
                    #     QMessageBox.critical(None, "Error", "Building morphology file has not been provided,"
                    #                                         " please check the main tab")
                    #     return
                    # elif os.path.isfile(self.IMPfile_path):
                    with open(self.IMPfile_path) as file:
                        next(file)
                        for line in file:
                            split = line.split()
                            if feat_id == int(split[0]):
                                IMP_heights_mean = split[3]
                                IMP_z0 = split[6]
                                IMP_zd = split[7]
                                IMP_fai = split[2]
                                found_IMP_line = True
                                break
                        if not found_IMP_line:
                            IMP_heights_mean = -999
                            IMP_z0 = -999
                            IMP_zd = -999
                            IMP_fai = -999
                            print_line = False
                    # else:
                    #     QMessageBox.critical(None, "Error",
                    #                          "Could not find the file containing building morphology")
                    #     return
                else:
                    IMP_heights_mean = feature.attribute(self.IMP_mean_height.getFieldName())
                    IMP_z0 = feature.attribute(self.IMP_z0.getFieldName())
                    IMP_zd = feature.attribute(self.IMP_zd.getFieldName())
                    IMP_fai = feature.attribute(self.IMP_fai.getFieldName())

                if self.IMPveg_from_file:
                    found_IMPveg_line = False

                    # if self.IMPvegfile_path is None:
                    #     QMessageBox.critical(None, "Error", "Building morphology file has not been provided,"
                    #                                         " please check the main tab")
                    #     return
                    # elif os.path.isfile(self.IMPvegfile_path):
                    with open(self.IMPvegfile_path) as file:
                        next(file)
                        for line in file:
                            split = line.split()
                            if feat_id == int(split[0]):
                                IMPveg_heights_mean_eve = split[3]
                                IMPveg_heights_mean_dec = split[3]
                                IMPveg_fai_eve = split[2]
                                IMPveg_fai_dec = split[2]
                                found_IMPveg_line = True
                                break
                        if not found_IMPveg_line:
                            IMPveg_heights_mean_eve = -999
                            IMPveg_heights_mean_dec = -999
                            IMPveg_fai_eve = -999
                            IMPveg_fai_dec = -999
                            print_line = False
                    # else:
                    #     QMessageBox.critical(None, "Error",
                    #                          "Could not find the file containing building morphology")
                    #     return
                else:
                    IMPveg_heights_mean_eve = feature.attribute(self.IMPveg_mean_height_eve.getFieldName())
                    IMPveg_heights_mean_dec = feature.attribute(self.IMPveg_mean_height_dec.getFieldName())
                    IMPveg_fai_eve = feature.attribute(self.IMPveg_fai_eve.getFieldName())
                    IMPveg_fai_dec = feature.attribute(self.IMPveg_fai_dec.getFieldName())

                if IMP_z0 == 0:
                    IMP_z0 = 0.03

                if IMP_zd == 0:
                    IMP_zd = 0.1

                code = "H_Bldgs"
                index = self.find_index(code)
                new_line[index] = str(IMP_heights_mean)
                code = "H_EveTr"
                index = self.find_index(code)
                new_line[index] = str(IMPveg_heights_mean_eve)
                code = "H_DecTr"
                index = self.find_index(code)
                new_line[index] = str(IMPveg_heights_mean_dec)
                code = "z0"
                index = self.find_index(code)
                new_line[index] = str(IMP_z0)
                code = "zd"
                index = self.find_index(code)
                new_line[index] = str(IMP_zd)
                code = "FAI_Bldgs"
                index = self.find_index(code)
                new_line[index] = str(IMP_fai)
                code = "FAI_EveTr"
                index = self.find_index(code)
                new_line[index] = str(IMPveg_fai_eve)
                code = "FAI_DecTr"
                index = self.find_index(code)
                new_line[index] = str(IMPveg_fai_dec)

                if self.pop_density is not None:
                    pop_density_night = feature.attribute(self.pop_density.getFieldName())
                    pop_density_day = feature.attribute(self.pop_density.getFieldName())
                else:
                    pop_density_night = -999
                    pop_density_day = -999

                code = "PopDensDay"
                index = self.find_index(code)
                new_line[index] = str(pop_density_day)
                code = "PopDensNight"
                index = self.find_index(code)
                new_line[index] = str(pop_density_night)

                for widget in self.widget_list:
                    if widget.get_checkstate():
                        code_field = str(widget.comboBox_uniquecodes.currentText())
                        try:
                            code = int(feature.attribute(code_field))
                        except ValueError as e:
                            QMessageBox.critical(None, "Error",
                                                 "Unique code field for widget " + widget.get_title() +
                                                 " should only contain integers")
                            return
                        match = widget.comboBox.findText(str(code))
                        if match == -1:
                            QMessageBox.critical(None, "Error",
                                                 "Unique code field for widget " + widget.get_title() +
                                                 " contains one or more codes with no match in site library")
                            return
                        index = widget.get_sitelistpos()
                        new_line[index - 1] = str(code)

                    else:
                        code = widget.get_combo_text()
                        index = widget.get_sitelistpos()
                        new_line[index - 1] = str(code)

                LUMPS_drate = 0.25
                LUMPS_Cover = 1
                LUMPS_MaxRes = 10
                NARP_Trans = 1

                code = "LUMPS_DrRate"
                index = self.find_index(code)
                new_line[index] = str(LUMPS_drate)
                code = "LUMPS_Cover"
                index = self.find_index(code)
                new_line[index] = str(LUMPS_Cover)
                code = "LUMPS_MaxRes"
                index = self.find_index(code)
                new_line[index] = str(LUMPS_MaxRes)
                code = "NARP_Trans"
                index = self.find_index(code)
                new_line[index] = str(NARP_Trans)

                flow_change = 0
                RunoffToWater = 0.1
                PipeCap = 100
                GridConn1of8 = 0
                Fraction1of8 = 0
                GridConn2of8 = 0
                Fraction2of8 = 0
                GridConn3of8 = 0
                Fraction3of8 = 0
                GridConn4of8 = 0
                Fraction4of8 = 0
                GridConn5of8 = 0
                Fraction5of8 = 0
                GridConn6of8 = 0
                Fraction6of8 = 0
                GridConn7of8 = 0
                Fraction7of8 = 0
                GridConn8of8 = 0
                Fraction8of8 = 0

                code = "FlowChange"
                index = self.find_index(code)
                new_line[index] = str(flow_change)
                code = "RunoffToWater"
                index = self.find_index(code)
                new_line[index] = str(RunoffToWater)
                code = "PipeCapacity"
                index = self.find_index(code)
                new_line[index] = str(PipeCap)
                code = "GridConnection1of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn1of8)
                code = "Fraction1of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction1of8)
                code = "GridConnection2of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn2of8)
                code = "Fraction2of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction2of8)
                code = "GridConnection3of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn3of8)
                code = "Fraction3of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction3of8)
                code = "GridConnection4of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn4of8)
                code = "Fraction4of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction4of8)
                code = "GridConnection5of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn5of8)
                code = "Fraction5of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction5of8)
                code = "GridConnection6of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn6of8)
                code = "Fraction6of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction6of8)
                code = "GridConnection7of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn7of8)
                code = "Fraction7of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction7of8)
                code = "GridConnection8of8"
                index = self.find_index(code)
                new_line[index] = str(GridConn8of8)
                code = "Fraction8of8"
                index = self.find_index(code)
                new_line[index] = str(Fraction8of8)

                WhitinGridPav = 661
                WhitinGridBldg = 662
                WhitinGridEve = 663
                WhitinGridDec = 664
                WhitinGridGrass = 665
                WhitinGridUnmanBsoil = 666
                WhitinGridWaterCode = 667

                code = "WithinGridPavedCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridPav)
                code = "WithinGridBldgsCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridBldg)
                code = "WithinGridEveTrCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridEve)
                code = "WithinGridDecTrCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridDec)
                code = "WithinGridGrassCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridGrass)
                code = "WithinGridUnmanBSoilCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridUnmanBsoil)
                code = "WithinGridWaterCode"
                index = self.find_index(code)
                new_line[index] = str(WhitinGridWaterCode)

                if self.wall_area_info:
                    wall_area = feature.attribute(self.wall_area.getFieldName())
                else:
                    wall_area = -999

                code = "AreaWall"
                index = self.find_index(code)
                new_line[index] = str(wall_area)

                Fr_ESTMClass_Paved1 = 1.
                Fr_ESTMClass_Paved2 = 0.
                Fr_ESTMClass_Paved3 = 0.
                Code_ESTMClass_Paved1 = 807
                Code_ESTMClass_Paved2 = 99999
                Code_ESTMClass_Paved3 = 99999
                Fr_ESTMClass_Bldgs1 = 1.0
                Fr_ESTMClass_Bldgs2 = 0.
                Fr_ESTMClass_Bldgs3 = 0.
                Fr_ESTMClass_Bldgs4 = 0.
                Fr_ESTMClass_Bldgs5 = 0.
                Code_ESTMClass_Bldgs1 = 801
                Code_ESTMClass_Bldgs2 = 99999
                Code_ESTMClass_Bldgs3 = 99999
                Code_ESTMClass_Bldgs4 = 99999
                Code_ESTMClass_Bldgs5 = 99999

                if self.land_use_from_file:
                    # if self.land_use_file_path is None:
                    #     QMessageBox.critical(None, "Error", "Land use fractions file has not been provided,"
                    #                                         " please check the main tab")
                    #     return
                    # if os.path.isfile(self.land_use_file_path):
                    with open(self.land_use_file_path) as file:
                        next(file)
                        found_LUF_line = False
                        for line in file:
                            split = line.split()
                            if feat_id == int(split[0]):
                                Fr_ESTMClass_Paved1 = split[1]
                                Fr_ESTMClass_Paved2 = split[2]
                                Fr_ESTMClass_Paved3 = split[3]
                                Code_ESTMClass_Paved1 = split[4]
                                Code_ESTMClass_Paved2 = split[5]
                                Code_ESTMClass_Paved3 = split[6]
                                Fr_ESTMClass_Bldgs1 = split[7]
                                Fr_ESTMClass_Bldgs2 = split[8]
                                Fr_ESTMClass_Bldgs3 = split[9]
                                Fr_ESTMClass_Bldgs4 = split[10]
                                Fr_ESTMClass_Bldgs5 = split[11]
                                Code_ESTMClass_Bldgs1 = split[12]
                                Code_ESTMClass_Bldgs2 = split[13]
                                Code_ESTMClass_Bldgs3 = split[14]
                                Code_ESTMClass_Bldgs4 = split[15]
                                Code_ESTMClass_Bldgs5 = split[16]

                                # if (float(Fr_ESTMClass_Paved1) + float(Fr_ESTMClass_Paved2) + float(Fr_ESTMClass_Paved3)) != 1:
                                #     QMessageBox.critical(None, "Error", "Land use fractions for paved not equal to 1 at " + str(feat_id))
                                #     return
                                #
                                # if (float(Fr_ESTMClass_Bldgs1) + float(Fr_ESTMClass_Bldgs2) + float(Fr_ESTMClass_Bldgs3) + float(Fr_ESTMClass_Bldgs4) + float(Fr_ESTMClass_Bldgs5)) != 1:
                                #     QMessageBox.critical(None, "Error", "Land use fractions for buildings not equal to 1 at " + str(feat_id))
                                #     return

                                found_LUF_line = True
                                break

                        # if not found_LUF_line:
                        #     Fr_ESTMClass_Paved1 = 1.
                        #     Fr_ESTMClass_Paved2 = 0.
                        #     Fr_ESTMClass_Paved3 = 0.
                        #     Code_ESTMClass_Paved1 = 807
                        #     Code_ESTMClass_Paved2 = 99999
                        #     Code_ESTMClass_Paved3 = 99999
                        #     Fr_ESTMClass_Bldgs1 = 1.0
                        #     Fr_ESTMClass_Bldgs2 = 0.
                        #     Fr_ESTMClass_Bldgs3 = 0.
                        #     Fr_ESTMClass_Bldgs4 = 0.
                        #     Fr_ESTMClass_Bldgs5 = 0.
                        #     Code_ESTMClass_Bldgs1 = 801
                        #     Code_ESTMClass_Bldgs2 = 99999
                        #     Code_ESTMClass_Bldgs3 = 99999
                        #     Code_ESTMClass_Bldgs4 = 99999
                        #     Code_ESTMClass_Bldgs5 = 99999
                    # else:
                    #     QMessageBox.critical(None, "Error",
                    #                          "Could not find the file containing land use cover fractions")
                    #     return
                # else:
                #     Fr_ESTMClass_Paved1 = 1.
                #     Fr_ESTMClass_Paved2 = 0.
                #     Fr_ESTMClass_Paved3 = 0.
                #     Code_ESTMClass_Paved1 = 807
                #     Code_ESTMClass_Paved2 = 99999
                #     Code_ESTMClass_Paved3 = 99999
                #     Fr_ESTMClass_Bldgs1 = 1.
                #     Fr_ESTMClass_Bldgs2 = 0.
                #     Fr_ESTMClass_Bldgs3 = 0.
                #     Fr_ESTMClass_Bldgs4 = 0.
                #     Fr_ESTMClass_Bldgs5 = 0.
                #     Code_ESTMClass_Bldgs1 = 801
                #     Code_ESTMClass_Bldgs2 = 99999
                #     Code_ESTMClass_Bldgs3 = 99999
                #     Code_ESTMClass_Bldgs4 = 99999
                #     Code_ESTMClass_Bldgs5 = 99999

                code = "Fr_ESTMClass_Bldgs1"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Bldgs1)
                code = "Fr_ESTMClass_Bldgs2"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Bldgs2)
                code = "Fr_ESTMClass_Bldgs3"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Bldgs3)
                code = "Fr_ESTMClass_Bldgs4"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Bldgs4)
                code = "Fr_ESTMClass_Bldgs5"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Bldgs5)
                code = "Fr_ESTMClass_Paved1"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Paved1)
                code = "Fr_ESTMClass_Paved2"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Paved2)
                code = "Fr_ESTMClass_Paved3"
                index = self.find_index(code)
                new_line[index] = str(Fr_ESTMClass_Paved3)
                code = "Code_ESTMClass_Bldgs1"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Bldgs1)
                code = "Code_ESTMClass_Bldgs2"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Bldgs2)
                code = "Code_ESTMClass_Bldgs3"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Bldgs3)
                code = "Code_ESTMClass_Bldgs4"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Bldgs4)
                code = "Code_ESTMClass_Bldgs5"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Bldgs5)
                code = "Code_ESTMClass_Paved1"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Paved1)
                code = "Code_ESTMClass_Paved2"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Paved2)
                code = "Code_ESTMClass_Paved3"
                index = self.find_index(code)
                new_line[index] = str(Code_ESTMClass_Paved3)

                new_line.append("!")

                if print_line: #TODO fix if only one init should be written.
                    self.lines_to_write.append(new_line)
                    # self.initial_conditions(year, feat_id)
                    nml = f90nml.read(self.input_path + 'InitialConditions.nml')
                    DaysSinceRain = self.day_since_rain
                    LeafCycle = self.leaf_cycle
                    SoilMoisture = self.soil_moisture
                    moist = int(int(SoilMoisture) * 1.5)

                    DailyMeanT = self.find_daily_mean_temp()

                    nml['initialconditions']['dayssincerain'] = int(DaysSinceRain)
                    nml['initialconditions']['temp_c0'] = float(DailyMeanT)
                    nml['initialconditions']['soilstorepavedstate'] = moist
                    nml['initialconditions']['soilstorebldgsstate'] = moist
                    nml['initialconditions']['soilstoreevetrstate'] = moist
                    nml['initialconditions']['soilstoredectrstate'] = moist
                    nml['initialconditions']['soilstoregrassstate'] = moist
                    nml['initialconditions']['soilstorebsoilstate'] = moist

                    f = open(self.Metfile_path, 'r')
                    lin = f.readlines()
                    index = 1
                    lines = np.array(lin[index].split())
                    nml['initialconditions']['id_prev'] = int(lines[1]) - 1
                    f.close()

                    if LeafCycle == 0:  # Winter
                        nml['initialconditions']['gdd_1_0'] = 0
                        nml['initialconditions']['gdd_2_0'] = -450
                        nml['initialconditions']['laiinitialevetr'] = 4
                        nml['initialconditions']['laiinitialdectr'] = 1
                        nml['initialconditions']['laiinitialgrass'] = 1.6
                    elif LeafCycle == 1:
                        nml['initialconditions']['gdd_1_0'] = 50
                        nml['initialconditions']['gdd_2_0'] = -400
                        nml['initialconditions']['laiinitialevetr'] = 4.2
                        nml['initialconditions']['laiinitialdectr'] = 2.0
                        nml['initialconditions']['laiinitialgrass'] = 2.6
                    elif LeafCycle == 2:
                        nml['initialconditions']['gdd_1_0'] = 150
                        nml['initialconditions']['gdd_2_0'] = -300
                        nml['initialconditions']['laiinitialevetr'] = 4.6
                        nml['initialconditions']['laiinitialdectr'] = 3.0
                        nml['initialconditions']['laiinitialgrass'] = 3.6
                    elif LeafCycle == 3:
                        nml['initialconditions']['gdd_1_0'] = 225
                        nml['initialconditions']['gdd_2_0'] = -150
                        nml['initialconditions']['laiinitialevetr'] = 4.9
                        nml['initialconditions']['laiinitialdectr'] = 4.5
                        nml['initialconditions']['laiinitialgrass'] = 4.6
                    elif LeafCycle == 4:  # Summer
                        nml['initialconditions']['gdd_1_0'] = 300
                        nml['initialconditions']['gdd_2_0'] = 0
                        nml['initialconditions']['laiinitialevetr'] = 5.1
                        nml['initialconditions']['laiinitialdectr'] = 5.5
                        nml['initialconditions']['laiinitialgrass'] = 5.9
                    elif LeafCycle == 5:
                        nml['initialconditions']['gdd_1_0'] = 225
                        nml['initialconditions']['gdd_2_0'] = -150
                        nml['initialconditions']['laiinitialevetr'] = 4.9
                        nml['initialconditions']['laiinitialdectr'] = 4, 5
                        nml['initialconditions']['laiinitialgrass'] = 4.6
                    # elif LeafCycle == 6:
                    #     nml['initialconditions']['gdd_1_0'] = 150
                    #     nml['initialconditions']['gdd_2_0'] = -300
                    #     nml['initialconditions']['laiinitialevetr'] = 4.6
                    #     nml['initialconditions']['laiinitialdectr'] = 3.0
                    #     nml['initialconditions']['laiinitialgrass'] = 3.6
                    elif LeafCycle == 6:  # dummy for londonsmall
                        nml['initialconditions']['gdd_1_0'] = 150
                        nml['initialconditions']['gdd_2_0'] = -300
                        nml['initialconditions']['laiinitialevetr'] = 4.6
                        nml['initialconditions']['laiinitialdectr'] = 5.0
                        nml['initialconditions']['laiinitialgrass'] = 5.6
                    elif LeafCycle == 7:
                        nml['initialconditions']['gdd_1_0'] = 50
                        nml['initialconditions']['gdd_2_0'] = -400
                        nml['initialconditions']['laiinitialevetr'] = 4.2
                        nml['initialconditions']['laiinitialdectr'] = 2.0
                        nml['initialconditions']['laiinitialgrass'] = 2.6

                    nml.write(self.output_dir[0] + '/InitialConditions' + str(self.file_code) + str(feat_id) + '_' + str(
                        year) + '.nml', force=True)

                # ind += 1
                self.progress.emit()

            output_lines = []
            output_file = self.output_dir[0] + "/SUEWS_SiteSelect.txt"
            with open(output_file, 'w+') as ofile:
                for line in self.lines_to_write:
                    string_to_print = ''
                    for element in line:
                        string_to_print += str(element) + '\t'
                    string_to_print += "\n"
                    output_lines.append(string_to_print)
                output_lines.append("-9\n")
                output_lines.append("-9\n")
                ofile.writelines(output_lines)
                for input_file in self.output_file_list:
                    try:
                        copyfile(self.output_path + input_file, self.output_dir[0] + "/" + input_file)
                    except IOError as e:
                        QgsMessageLog.logMessage(
                            "Error copying output files with SUEWS_SiteSelect.txt: " + str(e),
                            level=QgsMessageLog.CRITICAL)
                copyfile(self.Metfile_path, self.output_dir[0] + "/" + self.file_code + '_data.txt')
                QMessageBox.information(None, "Complete",
                                        "File successfully created as SUEWS_SiteSelect.txt in Output "
                                        "Folder: " + self.output_dir[0])

            if self.killed is False:
                self.progress.emit()
                ret = 1

        except Exception, e:
            ret = 0
            errorstring = self.print_exception()
            self.error.emit(errorstring)

        self.finished.emit(ret)

    def kill(self):
        self.killed = True

    def print_exception(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        return 'EXCEPTION IN {}, \nLINE {} "{}" \nERROR MESSAGE: {}'.format(filename, lineno, line.strip(), exc_obj)

    def find_index(self, code):
        values = self.header_sheet.row_values(1)
        index = values.index(code)
        return index

    def initial_conditions(self, year, gridid):
        nml = f90nml.read(self.input_path + 'InitialConditions.nml')
        DaysSinceRain = self.day_since_rain
        LeafCycle = self.leaf_cycle
        SoilMoisture = self.soil_moisture
        moist = int(int(SoilMoisture) * 1.5)

        DailyMeanT = self.find_daily_mean_temp()

        nml['initialconditions']['dayssincerain'] = int(DaysSinceRain)
        nml['initialconditions']['temp_c0'] = float(DailyMeanT)
        nml['initialconditions']['soilstorepavedstate'] = moist
        nml['initialconditions']['soilstorebldgsstate'] = moist
        nml['initialconditions']['soilstoreevetrstate'] = moist
        nml['initialconditions']['soilstoredectrstate'] = moist
        nml['initialconditions']['soilstoregrassstate'] = moist
        nml['initialconditions']['soilstorebsoilstate'] = moist

        f = open(self.Metfile_path, 'r')
        lin = f.readlines()
        index = 1
        lines = np.array(lin[index].split())
        nml['initialconditions']['id_prev'] = int(lines[1]) - 1
        f.close()

        if LeafCycle == 0:  # Winter
            nml['initialconditions']['gdd_1_0'] = 0
            nml['initialconditions']['gdd_2_0'] = -450
            nml['initialconditions']['laiinitialevetr'] = 4
            nml['initialconditions']['laiinitialdectr'] = 1
            nml['initialconditions']['laiinitialgrass'] = 1.6
        elif LeafCycle == 1:
            nml['initialconditions']['gdd_1_0'] = 50
            nml['initialconditions']['gdd_2_0'] = -400
            nml['initialconditions']['laiinitialevetr'] = 4.2
            nml['initialconditions']['laiinitialdectr'] = 2.0
            nml['initialconditions']['laiinitialgrass'] = 2.6
        elif LeafCycle == 2:
            nml['initialconditions']['gdd_1_0'] = 150
            nml['initialconditions']['gdd_2_0'] = -300
            nml['initialconditions']['laiinitialevetr'] = 4.6
            nml['initialconditions']['laiinitialdectr'] = 3.0
            nml['initialconditions']['laiinitialgrass'] = 3.6
        elif LeafCycle == 3:
            nml['initialconditions']['gdd_1_0'] = 225
            nml['initialconditions']['gdd_2_0'] = -150
            nml['initialconditions']['laiinitialevetr'] = 4.9
            nml['initialconditions']['laiinitialdectr'] = 4.5
            nml['initialconditions']['laiinitialgrass'] = 4.6
        elif LeafCycle == 4:  # Summer
            nml['initialconditions']['gdd_1_0'] = 300
            nml['initialconditions']['gdd_2_0'] = 0
            nml['initialconditions']['laiinitialevetr'] = 5.1
            nml['initialconditions']['laiinitialdectr'] = 5.5
            nml['initialconditions']['laiinitialgrass'] = 5.9
        elif LeafCycle == 5:
            nml['initialconditions']['gdd_1_0'] = 225
            nml['initialconditions']['gdd_2_0'] = -150
            nml['initialconditions']['laiinitialevetr'] = 4.9
            nml['initialconditions']['laiinitialdectr'] = 4, 5
            nml['initialconditions']['laiinitialgrass'] = 4.6
        # elif LeafCycle == 6:
        #     nml['initialconditions']['gdd_1_0'] = 150
        #     nml['initialconditions']['gdd_2_0'] = -300
        #     nml['initialconditions']['laiinitialevetr'] = 4.6
        #     nml['initialconditions']['laiinitialdectr'] = 3.0
        #     nml['initialconditions']['laiinitialgrass'] = 3.6
        elif LeafCycle == 6:  # dummy for londonsmall
            nml['initialconditions']['gdd_1_0'] = 150
            nml['initialconditions']['gdd_2_0'] = -300
            nml['initialconditions']['laiinitialevetr'] = 4.6
            nml['initialconditions']['laiinitialdectr'] = 5.0
            nml['initialconditions']['laiinitialgrass'] = 5.6
        elif LeafCycle == 7:
            nml['initialconditions']['gdd_1_0'] = 50
            nml['initialconditions']['gdd_2_0'] = -400
            nml['initialconditions']['laiinitialevetr'] = 4.2
            nml['initialconditions']['laiinitialdectr'] = 2.0
            nml['initialconditions']['laiinitialgrass'] = 2.6

        nml.write(self.output_dir[0] + '/InitialConditions' + str(self.file_code) + str(gridid) + '_' + str(year) + '.nml', force=True)

    def find_daily_mean_temp(self):
        if os.path.isfile(self.Metfile_path):
            with open(self.Metfile_path) as file:
                next(file)
                line = next(file)
                split = line.split()
                day = int(split[1])
                number_of_hours = 1
                total_temp = float(split[11])
                for line in file:
                    split = line.split()
                    if day == int(split[1]):
                        total_temp += float(split[11])
                        number_of_hours += 1

                mean_temp = float(total_temp) / int(number_of_hours)
                return mean_temp