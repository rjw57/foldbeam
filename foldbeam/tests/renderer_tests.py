import hashlib
import logging
import StringIO
import unittest
import os
import sys

import pyspatialite
sys.modules['pysqlite2'] = pyspatialite

import cairo
from filecache import filecache
from osgeo.osr import SpatialReference

import httplib2

from shapely.geometry import Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon
from shapely.geometry.polygon import LinearRing

from sqlalchemy import create_engine, MetaData
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import geoalchemy

from foldbeam.geometry import IterableGeometry, GeoAlchemyGeometry
from foldbeam.renderer import set_geo_transform, default_url_fetcher
from foldbeam.renderer import TileFetcher, Geometry
from foldbeam.renderer import Wrapped, Layers
from foldbeam.tests import surface_hash, output_surface

log = logging.getLogger()

def test_url_fetcher(url):
    """A cached version of the default URL fetcher. This function uses filecache to cache the results for 24 hours.
    """
    logging.info('Fetching URL: {0}'.format(url))
    http = httplib2.Http(os.path.join(os.path.dirname(__file__), 'httpcache'))
    rep, content = http.request(url, 'GET')
    if rep.status != 200:
        raise foldbeam.renderer.URLFetchError(str(rep.status) + ' ' + rep.reason)
    return content

class TestTileFetcher(unittest.TestCase):
    def setUp(self):
        # Create a cairo image surface
        sw, sh = (640, 480)
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        self.cr = cairo.Context(self.surface)
        self.cr.set_source_rgba(0,0,0,0)
        self.cr.paint()

    def centre_on_big_ben(self, width=500):
        # The EPSG:3857 co-ordinates of Big Ben, an easily identifiable landmark
        cx, cy = (-13871.6330672413, 6710328.3443702850)
        height = float(width * self.surface.get_height()) / float(self.surface.get_width())
        set_geo_transform(
                self.cr,
                cx-0.5*width, cx+0.5*width, cy+0.5*height, cy-0.5*height,
                self.surface.get_width(), self.surface.get_height())

    def centre_on_hawaii(self, width=500):
        # The EPSG:3857 co-ordinates of Hawaii
        cx, cy = (-17565813.6724973172, 2429047.3665894675)
        height = float(width * self.surface.get_height()) / float(self.surface.get_width())
        set_geo_transform(
                self.cr,
                cx-0.5*width, cx+0.5*width, cy+0.5*height, cy-0.5*height,
                self.surface.get_width(), self.surface.get_height())

    def test_default(self):
        self.centre_on_big_ben()
        renderer = TileFetcher(url_fetcher=test_url_fetcher)
        renderer.render(self.cr)
        output_surface(self.surface, 'tilefetcher_default')
        self.assertEqual(surface_hash(self.surface)/10, 723002)

    def test_aerial(self):
        self.centre_on_big_ben(1000e3)
        renderer = TileFetcher(
            url_pattern='http://oatile1.mqcdn.com/tiles/1.0.0/sat/{zoom}/{x}/{y}.jpg',
            url_fetcher=test_url_fetcher
        )
        renderer.render(self.cr)
        output_surface(self.surface, 'tilefetcher_aerial')
        self.assertEqual(surface_hash(self.surface)/10, 720869)

    def test_aerial_hawaii(self):
        # should be a large enough area to wrap over the -180/180 longitude
        self.centre_on_hawaii(7000e3) # 7000 km
        renderer = TileFetcher(
            url_pattern='http://oatile1.mqcdn.com/tiles/1.0.0/sat/{zoom}/{x}/{y}.jpg',
            url_fetcher=test_url_fetcher
        )
        renderer.render(self.cr)
        output_surface(self.surface, 'tilefetcher_aerial_hawaii')
        self.assertEqual(surface_hash(self.surface)/10, 545209)

    def test_british_national_grid(self):
        sw = int(671196.3657 - 1393.0196) / 1000
        sh = int(1230275.0454 - 13494.9764) / 1000
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        cr = cairo.Context(surface)

        # The valid range of the British national grid
        set_geo_transform(cr,
            1393.0196, 671196.3657, 1230275.0454, 13494.9764,
            surface.get_width(), surface.get_height()
        )

        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # OSGB 1936

        renderer = TileFetcher(url_fetcher=test_url_fetcher)
        renderer.render(cr, spatial_reference=srs)
        output_surface(surface, 'tilefetcher_british_national_grid')
        self.assertEqual(surface_hash(surface)/10, 1893451)

    def test_british_national_grid_upside_down(self):
        sw = int(671196.3657 - 1393.0196) / 1000
        sh = int(1230275.0454 - 13494.9764) / 1000
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        cr = cairo.Context(surface)

        # The valid range of the British national grid_upside_down
        set_geo_transform(cr,
            1393.0196, 671196.3657, 13494.9764, 1230275.0454,
            surface.get_width(), surface.get_height()
        )

        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # OSGB 1936

        renderer = TileFetcher(url_fetcher=test_url_fetcher)
        renderer.render(cr, spatial_reference=srs)
        output_surface(surface, 'tilefetcher_british_national_grid_upside_down')
        self.assertEqual(surface_hash(surface)/10, 1893451)

    def test_british_national_grid_mirrored(self):
        sw = int(671196.3657 - 1393.0196) / 1000
        sh = int(1230275.0454 - 13494.9764) / 1000
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        cr = cairo.Context(surface)

        # The valid range of the British national grid_mirrored
        set_geo_transform(cr,
            671196.3657, 1393.0196, 1230275.0454, 13494.9764,
            surface.get_width(), surface.get_height()
        )

        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # OSGB 1936

        renderer = TileFetcher(url_fetcher=test_url_fetcher)
        renderer.render(cr, spatial_reference=srs)
        output_surface(surface, 'tilefetcher_british_national_grid_mirrored')
        self.assertEqual(surface_hash(surface)/10, 1893451)

    def test_british_national_grid_wide(self):
        sw = 1200
        sh = 900
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        cr = cairo.Context(surface)

        # The valid range of the British national grid
        set_geo_transform(cr,
            -2400000, 2400000, 1800000, -1800000,
            surface.get_width(), surface.get_height()
        )

        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # OSGB 1936

        renderer = TileFetcher(url_fetcher=test_url_fetcher)
        renderer.render(cr, spatial_reference=srs)
        output_surface(surface, 'tilefetcher_british_national_grid_wide')
        self.assertEqual(surface_hash(surface)/10, 2560541)

    def test_british_national_grid_ultra_wide(self):
        sw = 1200
        sh = 900
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        cr = cairo.Context(surface)

        # The valid range of the British national grid
        set_geo_transform(cr,
            -4800000, 4800000, 3600000, -3600000,
            surface.get_width(), surface.get_height()
        )

        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # OSGB 1936

        renderer = TileFetcher(url_fetcher=test_url_fetcher)
        renderer.render(cr, spatial_reference=srs)
        output_surface(surface, 'tilefetcher_british_national_grid_ultra_wide')
        self.assertEqual(surface_hash(surface)/10, 2651647)

class TestGeometry(unittest.TestCase):
    def test_default(self):
        renderer = Geometry()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 360, 180)
        cr = cairo.Context(surface)
        renderer.render(cr)
        output_surface(surface, 'geometryrenderer_default')
        self.assertEqual(surface_hash(surface)/10, 51840)

    def test_points(self):
        geom = IterableGeometry([
            Point(0, 0),
            Point(-180, 0),
            Point(180, 0),
            Point(0, 90),
            Point(0, -90),
            Point(45, 45),
            Point(30, 10),
        ])
        renderer = Geometry(geom=geom)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 360, 180)
        cr = cairo.Context(surface)
        set_geo_transform(cr, -180, 180, 90, -90, 360, 180)

        srs = SpatialReference()
        srs.ImportFromEPSG(4326) # WGS84 lat/long

        cr.set_source_rgb(0,1,0)
        renderer.fill = True
        renderer.stroke = False
        renderer.render(cr, spatial_reference=srs)
        cr.set_source_rgb(0,0.5,0)
        renderer.fill = False
        renderer.stroke = True
        renderer.render(cr, spatial_reference=srs)

        output_surface(surface, 'geometryrenderer_points')
        self.assertEqual(surface_hash(surface)/10, 53314)

    def test_multipoints(self):
        geom = IterableGeometry([
            MultiPoint([
                Point(0, 0),
                Point(-180, 0),
                Point(180, 0),
                Point(0, 90),
                Point(0, -90),
                Point(45, 45),
                Point(30, 10),
            ])
        ])
        renderer = Geometry(geom=geom)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 360, 180)
        cr = cairo.Context(surface)
        set_geo_transform(cr, -180, 180, 90, -90, 360, 180)

        srs = SpatialReference()
        srs.ImportFromEPSG(4326) # WGS84 lat/long

        cr.set_source_rgb(0,1,0)
        renderer.fill = True
        renderer.stroke = False
        renderer.render(cr, spatial_reference=srs)
        cr.set_source_rgb(0,0.5,0)
        renderer.fill = False
        renderer.stroke = True
        renderer.render(cr, spatial_reference=srs)

        output_surface(surface, 'geometryrenderer_multipoints')
        self.assertEqual(surface_hash(surface)/10, 53314)

    def test_linestrings(self):
        geom = IterableGeometry([
            LineString([
                (0, 0),
                (-180, 0),
                (180, 0),
                (0, 90),
            ]),
            LineString([
                (0, -90),
                (45, 45),
                (30, 10),
            ]),
        ])
        renderer = Geometry(geom=geom)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 360, 180)
        cr = cairo.Context(surface)
        set_geo_transform(cr, -180, 180, 90, -90, 360, 180)

        srs = SpatialReference()
        srs.ImportFromEPSG(4326) # WGS84 lat/long

        cr.set_source_rgb(0.8,0,0)
        renderer.fill = False
        renderer.stroke = True
        renderer.render(cr, spatial_reference=srs)

        output_surface(surface, 'geometryrenderer_linestrings')
        self.assertEqual(surface_hash(surface)/10, 55488)

    def test_multilinestrings(self):
        geom = IterableGeometry([
            MultiLineString([
                LineString([
                    (0, 0),
                    (-180, 0),
                    (180, 0),
                    (0, 90),
                ]),
                LineString([
                    (0, -90),
                    (45, 45),
                    (30, 10),
                ]),
            ])
        ])
        renderer = Geometry(geom=geom)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 360, 180)
        cr = cairo.Context(surface)
        set_geo_transform(cr, -180, 180, 90, -90, 360, 180)

        srs = SpatialReference()
        srs.ImportFromEPSG(4326) # WGS84 lat/long

        cr.set_source_rgb(0.8,0,0)
        renderer.fill = False
        renderer.stroke = True
        renderer.render(cr, spatial_reference=srs)

        output_surface(surface, 'geometryrenderer_multilinestrings')
        self.assertEqual(surface_hash(surface)/10, 55488)

    def test_linearrings(self):
        geom = IterableGeometry([
            LinearRing([
                (0, 0),
                (-180, 0),
                (180, 0),
                (0, 90),
            ]),
            LinearRing([
                (0, -90),
                (45, 45),
                (30, 10),
            ]),
        ])
        renderer = Geometry(geom=geom)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 360, 180)
        cr = cairo.Context(surface)
        set_geo_transform(cr, -180, 180, 90, -90, 360, 180)

        srs = SpatialReference()
        srs.ImportFromEPSG(4326) # WGS84 lat/long

        cr.set_source_rgb(0.8,0,0)
        renderer.fill = False
        renderer.stroke = True
        renderer.render(cr, spatial_reference=srs)

        output_surface(surface, 'geometryrenderer_linearrings')
        self.assertEqual(surface_hash(surface)/10, 56042)

    def test_polygons(self):
        geom = IterableGeometry([
            Polygon(LinearRing([
                (0, 0),
                (-180, 0),
                (-180, 80),
                (20, 10),
            ])),
            Polygon(LinearRing([
                (30,30),
                (30,80),
                (100,80),
                (150,40),
                (100,30),
            ]), [
                LinearRing([
                    (50, 50),
                    (60, 70),
                    (70, 50),
                ]),
            ]),
        ])
        renderer = Geometry(geom=geom)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 360, 180)
        cr = cairo.Context(surface)
        set_geo_transform(cr, -180, 180, 90, -90, 360, 180)

        srs = SpatialReference()
        srs.ImportFromEPSG(4326) # WGS84 lat/long

        cr.set_source_rgba(0.8,0,0,0.7)
        renderer.fill = True
        renderer.stroke = False
        renderer.render(cr, spatial_reference=srs)

        cr.set_source_rgb(0.3,0,0)
        renderer.fill = False
        renderer.stroke = True
        renderer.render(cr, spatial_reference=srs)

        output_surface(surface, 'geometryrenderer_polygons')
        self.assertEqual(surface_hash(surface)/10, 65083)

    def test_multipolygons(self):
        geom = IterableGeometry([MultiPolygon([
            Polygon(LinearRing([
                (0, 0),
                (-180, 0),
                (-180, 80),
                (20, 10),
            ])),
            Polygon(LinearRing([
                (30,30),
                (30,80),
                (100,80),
                (150,40),
                (100,30),
            ]), [
                LinearRing([
                    (50, 50),
                    (60, 70),
                    (70, 50),
                ]),
            ]),
        ])])
        renderer = Geometry(geom=geom)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 360, 180)
        cr = cairo.Context(surface)
        set_geo_transform(cr, -180, 180, 90, -90, 360, 180)

        srs = SpatialReference()
        srs.ImportFromEPSG(4326) # WGS84 lat/long

        cr.set_source_rgba(0.8,0,0,0.7)
        renderer.fill = True
        renderer.stroke = False
        renderer.render(cr, spatial_reference=srs)

        cr.set_source_rgb(0.3,0,0)
        renderer.fill = False
        renderer.stroke = True
        renderer.render(cr, spatial_reference=srs)

        output_surface(surface, 'geometryrenderer_multipolygons')
        self.assertEqual(surface_hash(surface)/10, 65083)

def osm_map_renderer(url_fetcher=None, use_postgres=False):
    osm_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/central-cambridge.sqlite'))
    # engine = create_engine('postgresql://gis:gis@localhost/central-cambridge')
    engine = create_engine('sqlite:///' + osm_db_path,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool)
    session = sessionmaker(bind=engine)

    Base = declarative_base(metadata=MetaData(engine, reflect=True))

    class PgLandUse(Base):
        __tablename__ = 'pg_landuse'
        __table_args__ = {'autoload': True, 'extend_existing': True}
        Geometry = geoalchemy.GeometryColumn(geoalchemy.MultiPolygon(dimension=2))

    class PgBuilding(Base):
        __tablename__ = 'pg_building'
        __table_args__ = {'autoload': True, 'extend_existing': True}
        Geometry = geoalchemy.GeometryColumn(geoalchemy.MultiPolygon(dimension=2))

    class PgAmenity(Base):
        __tablename__ = 'pg_amenity'
        __table_args__ = {'autoload': True, 'extend_existing': True}
        Geometry = geoalchemy.GeometryColumn(geoalchemy.MultiPolygon(dimension=2))

    class LnHighway(Base):
        __tablename__ = 'ln_highway'
        __table_args__ = {'autoload': True, 'extend_existing': True}
        Geometry = geoalchemy.GeometryColumn(geoalchemy.MultiLineString(dimension=2))

    class PtShop(Base):
        __tablename__ = 'pt_shop'
        __table_args__ = {'autoload': True, 'extend_existing': True}
        Geometry = geoalchemy.GeometryColumn(geoalchemy.MultiPoint(dimension=2))

    def query(cls):
        def f(cls=cls):
            return session().query(cls)
        return f

    wgs84 = SpatialReference()
    wgs84.ImportFromEPSG(4326) # WGS84 lat/long

    bng = SpatialReference()
    bng.ImportFromEPSG(27700) # British national grid

    land_use = GeoAlchemyGeometry(
            query(PgLandUse),
            geom_cls=PgLandUse, geom_attr='Geometry',
            spatial_reference=wgs84)

    building = GeoAlchemyGeometry(
            query(PgBuilding),
            geom_cls=PgBuilding, geom_attr='Geometry',
            spatial_reference=wgs84)

    amenity = GeoAlchemyGeometry(
            query(PgAmenity),
            geom_cls=PgAmenity, geom_attr='Geometry',
            spatial_reference=wgs84)

    highway = GeoAlchemyGeometry(
            query(LnHighway),
            geom_cls=LnHighway, geom_attr='Geometry',
            spatial_reference=wgs84)

    shop = GeoAlchemyGeometry(
            query(PtShop),
            geom_cls=PtShop, geom_attr='Geometry',
            spatial_reference=wgs84)

    # Return a callable to set line width and source colour
    def prepare(rgba=None, lw=None):
        def f(cr, rgba=rgba, lw=lw):
            metres_per_point = max([abs(x) for x in cr.device_to_user_distance(1,1)])
            rgba = rgba or (0,0,0,1)
            cr.set_source_rgba(*rgba)
            cr.set_line_width((lw or 1.0) * metres_per_point)
        return f

    # Create a renderer for the entire map
    map_renderer = Layers(layers=[])

    # Create a renderer for the base layer. By default this will fetch MapQuest tiles. Provide a custom caching URL
    # fetcher so we're kinder to MapQuest's servers.
    map_renderer.layers.append(TileFetcher(url_fetcher=url_fetcher or test_url_fetcher))
    
    # Fill building boundary polygons in translucent blue with a dark blue outline
    # with a line width of 2 points == 2 / 72 in. (Device units are points for PDF.)
    map_renderer.layers.append(Geometry(
        geom=building,
        fill=True, prepare_fill=prepare(rgba=(0,0,0.5,0.5)),
        stroke=True, prepare_stroke=prepare(rgba=(0,0,0.5,1), lw=2.0),
    ))

    # Fill amenity boundary polygons in translucent red with a dark red outline
    map_renderer.layers.append(Geometry(
        geom=amenity,
        fill=True, prepare_fill=prepare(rgba=(0.5,0,0,0.25)),
        stroke=True, prepare_stroke=prepare(rgba=(0.5,0,0,1), lw=2.0),
    ))

    # Fill land-use boundary polygons in translucent green
    map_renderer.layers.append(Wrapped(
        Geometry(geom=land_use, fill=True, stroke=False),
        pre=prepare(rgba=(0,0.5,0,0.25))
    ))

    # Stroke roads firstly in black, then overlay in yellow
    map_renderer.layers.append(Wrapped(
        Geometry(geom=highway),
        pre=prepare(rgba=(0,0,0,1), lw=3.5)
    ))
    map_renderer.layers.append(Wrapped(
        Geometry(geom=highway),
        pre=prepare(rgba=(0.9,0.8,0,1), lw=2.0)
    ))

    # Draw shop locations in orange
    map_renderer.layers.append(Geometry(
        geom=shop,
        fill=True, prepare_fill=prepare(rgba=(0.6,0.3,0,0.5)),
        stroke=True, prepare_stroke=prepare(rgba=(0.6,0.3,0,1)),
        marker_radius=3.0
    ))

    if use_postgres:
        stops_engine = create_engine('postgresql://gis:gis@localhost/public_transport')
        stops_session = sessionmaker(bind=stops_engine)

        Base = declarative_base(metadata=MetaData(stops_engine, reflect=True))

        class Stops(Base):
            __tablename__ = 'stops'
            __table_args__ = {'autoload': True, 'extend_existing': True}
            Geometry = geoalchemy.GeometryColumn(geoalchemy.Point(dimension=2, srid=27700))

        def stops_query(cls):
            def f(cls=cls):
                return stops_session().query(cls).filter(cls.naptancode.like('cmb%'))
            return f

        stops = GeoAlchemyGeometry(
                stops_query(Stops),
                geom_cls=Stops, geom_attr='Geometry',
                spatial_reference=bng,
                db_srid=27700)

        map_renderer.layers.append(Geometry(
            geom=stops,
            fill=True, prepare_fill=prepare(rgba=(0.6,0,0.5,0.5)),
            stroke=True, prepare_stroke=prepare(rgba=(0.6,0,0.5,1)),
            marker_radius=3.0
        ))

    return map_renderer

class TestOSMGeometry(unittest.TestCase):
    def setUp(self):
        self.map_renderer = osm_map_renderer()

    def test_osm(self):
        # Create an output image surface for the map at 640x360 pixels.
        sw, sh = (640, 360)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)

        # We will be using the British National Grid (OSGB 1936) as the map projestion
        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # British National Grid

        # Create a context for the output and centre it on Cambridge. Set the scale to be 10 metres to 1 cm (1000:1).
        cr = cairo.Context(surface)
        cx, cy = (544783, 258469) # BNG co-ordinates for Cambridge
        metres_per_point = (2.54 * 10.0) / (72.0) # convert points -> inches -> cm -> 10 metres/cm
        w, h = [dist * metres_per_point for dist in (sw, sh)]
        set_geo_transform(cr, cx-0.5*w, cx+0.5*w, cy+0.5*h, cy-0.5*h, sw, sh)

        # Actually render the map
        self.map_renderer.render(cr, spatial_reference=srs)

        output_surface(surface, 'geometryrenderer_osm')
        self.assertEqual(surface_hash(surface)/10, 590026)

    def test_osm_pdf(self):
        # Create an output PDF surface for the map at 8.27x11.69 in (A4).
        sw, sh = (int(8.27*72), int(11.69*72))
        surface = cairo.PDFSurface('central-cambridge.pdf', sw, sh)

        # We will be using the British National Grid (OSGB 1936) as the map projestion
        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # British National Grid

        # Create a context for the output and centre it on Cambridge. Set the scale to be 10 metres to 1 cm (1000:1).
        cr = cairo.Context(surface)
        cx, cy = (544783, 258469) # BNG co-ordinates for Cambridge
        metres_per_point = (2.54 * 10.0) / (72.0) # convert points -> inches -> cm -> 10 metres/cm
        w, h = [dist * metres_per_point for dist in (sw, sh)]
        set_geo_transform(cr, cx-0.5*w, cx+0.5*w, cy+0.5*h, cy-0.5*h, sw, sh)

        # Actually render the map
        self.map_renderer.render(cr, spatial_reference=srs)

        # Write the first page of the output
        cr.show_page()

