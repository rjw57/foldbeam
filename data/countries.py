import mapnik
m = mapnik.Map(1024,512)
mapnik.load_map(m,'countries.xml')
m.srs = '+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +datum=OSGB36 +units=m +no_defs'
m.zoom_to_box(mapnik.Box2d(-2e6, -0.5e6, 2e6, 1.5e6))
mapnik.render_to_file(m, 'map.png')

