"""
History:

Tried first with methods of QgsVectorFileWriter, but methods did not create
database or table name could not be specified. Changed to classes of the
db_manager plugin (is a standard plugin of QGIS, provided with each
installation)
"""
from functools import wraps
import os

from qgis.core import QGis, QgsDataSourceURI, QgsVectorLayer
from db_manager.db_plugins.spatialite.connector import SpatiaLiteDBConnector
from PyQt4.QtCore import QVariant
from osgeo import ogr
from osgeo import gdal

from ..utils.user_messages import log

ogr.UseExceptions()  # better exceptions


def disable_sqlite_synchronous(func):
    """
    Decorator for temporarily disabling the 'OGR_SQLITE_SYNCHRONOUS' global
    option. Without doing this creating a spatialite file fails (doesn't
    complete or incredibly slow) under Ubuntu 14.04.

    Note: shouldn't be needed anymore in newer versions of GDAL.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if int(gdal.VersionInfo()) < 2000000:
            gdal.SetConfigOption('OGR_SQLITE_SYNCHRONOUS', 'OFF')
        retval = func(*args, **kwargs)
        if int(gdal.VersionInfo()) < 2000000:
            gdal.SetConfigOption('OGR_SQLITE_SYNCHRONOUS', 'FULL')
        return retval
    return wrapper


class Spatialite(SpatiaLiteDBConnector):

    def __init__(self, path, create_if_not_exist=True):
        self.path = path
        uri = self._get_uri()
        if create_if_not_exist and not os.path.isfile(self.path):
            # create empty spatialite
            spatialite = self._create_empty_database()
            if spatialite is None:
                raise IOError(
                    'Unable to create empty spatialite "{0}"'.format(path))
            spatialite = None
        SpatiaLiteDBConnector.__init__(self, uri)

    def _get_uri(self, table_name=None, geom_field='the_geom'):
        uri = QgsDataSourceURI()
        uri.setDatabase(self.path)
        if table_name is not None:
            schema = ''
            uri.setDataSource(schema, table_name, geom_field)

        return uri

    @disable_sqlite_synchronous
    def _create_empty_database(self):
        drv = ogr.GetDriverByName('SQLite')
        db = drv.CreateDataSource(self.path, ["SPATIALITE=YES"])
        return db

    def get_layer(self, table_name, display_name=None, geom_field='the_geom'):

        if display_name is None:
            display_name = table_name

        uri = self._get_uri(table_name, geom_field)
        layer = QgsVectorLayer(uri.uri(), display_name, 'spatialite')

        if layer.isValid():
            return layer
        else:
            log('error loading table {table_name} from spatialite file '
                '{path}. Error message: {error}.'.format(table_name=table_name,
                                                         path=self.path,
                                                         error=layer.error()))
            return None

    def import_layer(
            self, layer, table_name, id_field=None, geom_field='the_geom',
            srid=4326):
        mapping = {
            int(QVariant.Int): 'INTEGER',
            int(QVariant.Double): 'DOUBLE',
            int(QVariant.TextFormat): 'TEXT',
            int(QVariant.Bool): 'BOOLEAN',
            int(QVariant.String): 'STRING'
        }

        sql_fields = []
        for field in layer.fields():
            tp = mapping[int(field.type())]

            if tp == 'STRING':
                sql_fields.append("{0} {1}({2})".format(field.name(),
                                                        tp,
                                                        field.length()))
            else:
                sql_fields.append("{0} {1}".format(field.name(), tp))

        self.createTable(table_name, sql_fields, id_field)

        geom_type = QGis.vectorGeometryType(layer.geometryType()).lstrip('WKB')
        self.addGeometryColumn(
            table_name, geom_field, geom_type=geom_type, srid=srid)

        splayer = self.get_layer(table_name, None, geom_field)
        splayer.addFeatures([feat for feat in layer.getFeatures()])

        self.createSpatialIndex(table_name, geom_field)

        return splayer

    def create_empty_layer(
            self, table_name, wkb_type=QGis.WKBPoint, fields=None,
            id_field='id', geom_field='the_geom', srid=4326):

        self.createTable(table_name, fields, id_field)
        geom_type = QGis.featureType(wkb_type).lstrip('WKB')
        self.addGeometryColumn(
            table_name, geom_field, geom_type=geom_type, srid=srid)
        self.createSpatialIndex(table_name, geom_field)

        return self.get_layer(table_name, None, geom_field)
