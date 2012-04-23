import tango
import boundsutils
import cairoutils
import goocanvas
import gobject
import simple
import math
import cairo

# Various orientations of the widget.
NE, NW, SE, SW = range(4)

class ResizeGadget(goocanvas.Rect, simple.SimpleItem, goocanvas.Item):
	__gproperties__ = {
		'orientation': ( int, None, None, 0, 3, 0, gobject.PARAM_READWRITE ) ,
		'color-scheme': ( str, None, None, 'Plum', gobject.PARAM_READWRITE ) ,
	}

	def __init__(self, *args, **kwargs):
		self._bounds = goocanvas.Bounds()
		self._color = (1.0, 1.0, 1.0, 0.33)
		self._resize_data = {
			'orientation': tango.RIGHT,
			'color-scheme': 'Plum',
		}

		goocanvas.Rect.__init__(self, *args, **kwargs)
	
	def _get_internal_bounds(self):
		internal_bounds = boundsutils.align_to_integer_boundary( \
			goocanvas.Bounds(
				self.get_property('x'),
				self.get_property('y'),
				self.get_property('x') + self.get_property('width'),
				self.get_property('y') + self.get_property('height')))
		return internal_bounds
	
	def get_color_scheme(self):
		return self.get_property('color-scheme')
	
	def set_color_scheme(self, color_scheme):
		self.set_property('color-scheme', color_scheme)
	
	def get_orientation(self):
		return self.get_property('orientation')
	
	def set_orientation(self, orientation):
		self.set_property('orientation', orientation)
	
	## gobject methods
	def do_get_property(self, pspec):
		names = self._resize_data.keys()
		if(pspec.name in names):
			return self._resize_data[pspec.name]
		else:
			return goocanvas.Rect.do_get_property(self, pspec)
	
	def do_set_property(self, pspec, value):
		names = self._resize_data.keys()
		if(pspec.name in names):
			self._resize_data[pspec.name] = value
			self.notify(pspec.name)
		else:
			goocanvas.Rect.do_set_property(self, pspec, value)
	
	## simple item methods
	def set_model(self, model):
		goocanvas.Rect.do_set_model(self, model)

	def do_simple_is_item_at(self, x, y, cr, is_pointer_event):
		return simple.SimpleItem.do_simple_is_item_at(
			self, x, y, cr, is_pointer_event)

	def do_simple_create_path(self, cr):
		# For hit testing
		cairoutils.rounded_rect(cr, self._get_internal_bounds(), 0, 0)
	
	def do_simple_paint(self, cr, bounds):
		my_bounds = self.get_bounds()
		if(not boundsutils.do_intersect(my_bounds, bounds)):
			return

		my_bounds = boundsutils.inset(self._get_internal_bounds(), 0.5, 0.5)

		width = my_bounds.x2 - my_bounds.x1
		height = my_bounds.y2 - my_bounds.y1
		size = int(math.floor(min(width, height)))

		orientation = self.get_orientation()

		if((orientation == SE) or (orientation == NE)):
			xsign = -1
			xstart = my_bounds.x2
		else:
			xsign = 1
			xstart = my_bounds.x2 - size

		if((orientation == NE) or (orientation == NW)):
			ysign = 1
			ystart = my_bounds.y2 - size
		else:
			ysign = -1
			ystart = my_bounds.y2

		cr.new_path()
		for offset in range(4, size, 3):
			cr.move_to(xstart + (xsign * offset), ystart)
			cr.line_to(xstart, ystart + (ysign * offset))

		color = list(tango.get_color_float_rgb( \
			self.get_color_scheme(), tango.LIGHT_CONTRAST))
		color.append(0.5)
		cr.set_source_rgba(*color)
		cr.set_line_cap(cairo.LINE_CAP_ROUND)
		cr.set_line_width(1.0)
		cr.stroke()

gobject.type_register(ResizeGadget)

# vim:sw=4:ts=4:autoindent
