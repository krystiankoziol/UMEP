# -*- coding: utf-8 -*-

"""
/***************************************************************************
 ProcessingUMEP
                                 A QGIS plugin
 UMEP for processing toolbox
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-04-02
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

__author__ = 'Fredrik Lindberg'
__date__ = '2020-04-02'
__copyright__ = '(C) 2020 by Fredrik Lindberg'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.core import QgsProcessingProvider
from processing.core.ProcessingConfig import ProcessingConfig
from .processor.shadow_generator_algorithm import ProcessingShadowGeneratorAlgorithm
from .preprocessor.wall_heightaspect_algorithm import ProcessingWallHeightAscpetAlgorithm
from .preprocessor.skyviewfactor_algorithm import ProcessingSkyViewFactorAlgorithm
from .preprocessor.copernicusera5_algorithm import ProcessingCopernicusERA5Algorithm
from .preprocessor.imagemorphparmspoint_algorithm import ProcessingImageMorphParmsPointAlgorithm
from .preprocessor.imagemorphparms_algorithm import ProcessingImageMorphParmsAlgorithm
from .preprocessor.landcoverfractionpoint_algorithm import ProcessingLandCoverFractionPointAlgorithm
from.preprocessor.landcoverfraction_algorithm import ProcessingLandCoverFractionAlgorithm
from .processor.suews_algorithm import ProcessingSuewsAlgorithm
import os.path
from qgis.PyQt.QtGui import QIcon
import inspect
# from PyQt5.QtGui import QIcon

class ProcessingUMEPProvider(QgsProcessingProvider):

    def __init__(self):
        """
        Default constructor.
        """
        self.plugin_dir = os.path.dirname(__file__)
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        #Preprocessor
        self.addAlgorithm(ProcessingSkyViewFactorAlgorithm())
        self.addAlgorithm(ProcessingWallHeightAscpetAlgorithm())
        self.addAlgorithm(ProcessingImageMorphParmsPointAlgorithm())
        self.addAlgorithm(ProcessingCopernicusERA5Algorithm())
        self.addAlgorithm(ProcessingImageMorphParmsAlgorithm())
        self.addAlgorithm(ProcessingLandCoverFractionPointAlgorithm())
        self.addAlgorithm(ProcessingLandCoverFractionAlgorithm())
        
        #Processor
        self.addAlgorithm(ProcessingShadowGeneratorAlgorithm())
        self.addAlgorithm(ProcessingSuewsAlgorithm())

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return 'umep'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return 'UMEP'
        
    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        icon = QIcon(os.path.dirname(__file__) + "/icons/icon_umep.png")
        return icon

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()