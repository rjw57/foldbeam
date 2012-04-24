import tango
import boundsutils
import cairoutils
import goocanvas
import gobject

class SimpleItem:
	## simple item methods
	def do_simple_is_item_at(self, x, y, cr, is_pointer_event):
		pointer_events = goocanvas.EVENTS_ALL
		self.do_simple_create_path(cr)
		if(self.check_in_path(x, y, cr, pointer_events)):
			return True
		return False

# vim:sw=4:ts=4:autoindent
