import tango
import boundsutils
import cairoutils
import goocanvas
import gobject
import simple

class TangoRectItem(goocanvas.Rect, simple.SimpleItem, goocanvas.Item):
	__gproperties__ = {
		'color-scheme':	(str, None, None, 'Plum',
			gobject.PARAM_READWRITE),
	}

	def __init__(self, *args, **kwargs):
		self._bounds = goocanvas.Bounds()
		self._data = {
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
	
	def get_interior_bounds(self):
		''' Return the bounds of the rectangle's interior in the
			item's logal space. '''

		internal_bounds = self._get_internal_bounds()

		return boundsutils.inset(internal_bounds, 3.0, 3.0)
	
	def get_color_scheme(self):
		return self.get_property('color-scheme')
	
	def set_color_scheme(self, scheme):
		self.set_property('color-scheme', scheme)

	## gobject methods
	def do_get_property(self, pspec):
		if(pspec.name == 'color-scheme'):
			return self._data['color-scheme']
		else:
			return goocanvas.Rect.do_get_property(self, pspec)
	
	def do_set_property(self, pspec, value):
		if(pspec.name == 'color-scheme'):
			if(not value in tango.get_scheme_names()):
				raise ValueError( \
					'%s is not a valid Tango color scheme' % value)
			self._data['color-scheme'] = value
			self.request_update()
			self.notify(pspec.name)
		else:
			goocanvas.Rect.do_set_property(self, pspec, value)
	
	## simple item methods
	def set_model(self, model):
		goocanvas.Rect.do_set_model(self, model)

		# So nefarious...
		self._data = model._data

	def do_simple_is_item_at(self, x, y, cr, is_pointer_event):
		return simple.SimpleItem.do_simple_is_item_at(
			self, x, y, cr, is_pointer_event)

	def do_simple_create_path(self, cr):
		# For hit testing
		(rx, ry) = self.get_properties('radius-x', 'radius-y')
		cairoutils.rounded_rect(cr, self._get_internal_bounds(), rx, ry)
	
	def do_simple_paint(self, cr, bounds):
		my_bounds = self.get_bounds()
		if(not boundsutils.do_intersect(my_bounds, bounds)):
			return

		internal_bounds = self._get_internal_bounds()

		(rx, ry) = self.get_properties('radius-x', 'radius-y')
		tango.paint_rounded_rect(cr, self.get_color_scheme(),
			internal_bounds, rx, ry, tango.IN)

gobject.type_register(TangoRectItem)

class TangoRectModel(goocanvas.RectModel, goocanvas.ItemModel):
	__gproperties__ = {
		'color-scheme':	(str, None, None, 'Plum',
			gobject.PARAM_READWRITE),
	}

	def __init__(self, *args, **kwargs):
		self._data = {
			'color-scheme': 'Plum',
		}

		goocanvas.RectModel.__init__(self, *args, **kwargs)

	## gobject methods
	def do_get_property(self, pspec):
		if(pspec.name == 'color-scheme'):
			return self._data['color-scheme']
		else:
			return goocanvas.RectModel.do_get_property(self, pspec)
	
	def do_set_property(self, pspec, value):
		if(pspec.name == 'color-scheme'):
			if(not value in tango.get_scheme_names()):
				raise ValueError( \
					'%s is not a valid Tango color scheme' % value)
			self._data['color-scheme'] = value
			self.emit('changed', False)
			self.notify(pspec.name)
		else:
			goocanvas.RectModel.do_set_property(self, pspec, value)
	
	## item model methods
	def do_create_item(self, canvas):
		item = TangoRectItem()
		item.set_model(self)
		item.set_canvas(canvas)
		return item

gobject.type_register(TangoRectModel)


# vim:sw=4:ts=4:autoindent
