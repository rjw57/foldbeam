import cairo
import cairoutils
import boundsutils
import math

# shades
LIGHT = 0
MEDIUM = 1
DARK = 2

# contrasting colours to shades
LIGHT_CONTRAST = 3
MEDIUM_CONTRAST = 4
DARK_CONTRAST = 5

# directions
IN = 0
OUT = 1

# orientations
TOP = 0
BOTTOM = 1
LEFT = 2
RIGHT = 3

def get_scheme_names():
	return _tango_palette.keys()

def get_color_int_rgb(scheme, shade):
	''' return a Tango colour from a particular scheme. shade
		is one of LIGHT, MEDIUM or DARK. The colour is returned
		as a RGB tuple with each channel in range 0-255. '''
	if(shade > DARK):
		flag = _tango_palette[scheme][3][shade - LIGHT_CONTRAST]
		if(flag == 1):
			c = get_color_int_rgb(scheme, LIGHT)
			return (int(0.5*(c[0]+255)), int(0.5*(c[1]+255)),
				int(0.5*(c[2]+255)))
		else:
			c = get_color_int_rgb(scheme, DARK)
			return (int(0.5*(c[0]+0)), int(0.5*(c[1]+0)),
				int(0.5*(c[2]+0)))
	return _tango_palette[scheme][shade]

def get_color_hex_string_rgb(scheme, shade):
	return '#%02x%02x%02x' % get_color_int_rgb(scheme, shade)

def get_color_float_rgb(scheme, shade):
	int_rgb = get_color_int_rgb(scheme, shade)
	return (int_rgb[0]/255.0, int_rgb[1]/255.0, int_rgb[2]/255.0)

def cairo_set_source(cr, scheme, shade):
	colour = get_color_float_rgb(scheme, shade)
	cr.set_source_rgb(*colour)

def cairo_pattern_add_color_stop(pattern, offset, scheme, shade, alpha):
	colour = get_color_float_rgb(scheme, shade)
	pattern.add_color_stop_rgba(offset,
		colour[0], colour[1], colour[2], alpha)

def _pad_make_curve(cr, cx, cy, radius, extent, orientation):
	if(orientation == RIGHT):
		start_angle = 0.5 * math.pi
		end_angle = 1.5 * math.pi
		x1 = cx + extent
		x2 = cx + extent
		y1 = cy + radius
		y2 = cy - radius
		x3 = cx
		y3 = y1
	elif(orientation == LEFT):
		start_angle = 1.5 * math.pi
		end_angle = 2.5 * math.pi
		x1 = cx - extent
		x2 = cx - extent
		y1 = cy - radius
		y2 = cy + radius
		x3 = cx
		y3 = y1
	elif(orientation == TOP):
		start_angle = 0.0
		end_angle = 1.0 * math.pi
		x1 = cx + radius
		y1 = cy - extent
		x2 = cx - radius
		y2 = cy - extent
		x3 = x1
		y3 = cy
	elif(orientation == BOTTOM):
		start_angle = 1.0 * math.pi
		end_angle = 2.0 * math.pi
		x1 = cx - radius
		y1 = cy + extent
		x2 = cx + radius
		y2 = cy + extent
		x3 = x1
		y3 = cy
	else:
		raise ValueError('Invalid orientation')

	cr.new_path()
	cr.move_to(x1, y1)
	cr.line_to(x3, y3)
	cr.save()
	cr.translate(cx, cy)
	cr.scale(radius, radius)
	cr.arc(0.0, 0.0, 1.0, start_angle, end_angle)
	cr.restore()
	cr.line_to(x2, y2)
	cr.close_path()

def pad_extents(x, y, orientation, size):
	''' Returns the extent of the pad
		as a tuple (minx, miny, maxx, maxy). '''
	radius = size * 0.5
	extent = math.ceil(0.62 * radius) + 0.5 # Golden ratio

	if(orientation == RIGHT):
		return (x - extent, y - radius, x, y + radius)
	elif(orientation == LEFT):
		return (x, y - radius, x + extent, y + radius)
	elif(orientation == TOP):
		return (x - radius, y - extent, x + radius, y + radius)
	elif(orientation == BOTTOM):
		return (x - radius, y - radius, x + radius, y + extent)
	else:
		raise ValueError('Invalid orientation')

def pad_get_centre(x, y, orientation, size):
	radius = size * 0.5
	extent = math.ceil(0.62 * radius) + 0.5 # Golden ratio

	if(orientation == RIGHT):
		cx = x - extent
		cy = y
	elif(orientation == LEFT):
		cx = x + extent
		cy = y
	elif(orientation == TOP):
		cx = x
		cy = y + extent
	elif(orientation == BOTTOM):
		cx = x
		cy = y - extent
	else:
		raise ValueError('Invalid orientation')

	return (cx, cy)

def pad_boundary_curve(cr, x, y, orientation, size):
	''' Set the current Cairo curve to the boundary of the
		specified pad. '''
	radius = size * 0.5
	extent = math.ceil(0.62 * radius) + 0.5 # Golden ratio
	(cx, cy) = pad_get_centre(x, y, orientation, size)
	_pad_make_curve(cr, cx, cy, radius, extent, orientation)

def paint_pad(cr, scheme, x, y, orientation, size, *args):
	''' Paint a connection pad anchored at (x,y) with specified
	    orientation. The anchor is taken to be the centre of
		the 'orientation' edge. The pad size is 'size'. 
		Optionally takes a bool indicating if the pad is 
		highlighted (default: False).'''

	radius = size * 0.5
	extent = math.ceil(0.62 * radius) + 0.5 # Golden ratio

	if(len(args) > 0):
		highlight = args[0]

	(cx, cy) = pad_get_centre(x, y, orientation, size)
	_pad_make_curve(cr, cx, cy, radius - 0.5, extent - 0.5, orientation)
	(minx,miny,maxx,maxy) = pad_extents(x,y,orientation,size)

	# Draw the light 'inner'
	if(highlight):
		cairo_set_source(cr, scheme, LIGHT)
	else:
		linear_blend = cairo.LinearGradient(minx,miny,maxx,maxy)
		cairo_pattern_add_color_stop(linear_blend, 
			0.0, scheme, MEDIUM, 1.0)
		cairo_pattern_add_color_stop(linear_blend, 
			1.0, scheme, LIGHT, 1.0)
		cr.set_source(linear_blend)
	cr.set_line_width(0.0)
	cr.fill_preserve()

	# Draw the dark 'outer' border
	linear_blend = cairo.LinearGradient(minx,miny,maxx,maxy)
	cairo_pattern_add_color_stop(linear_blend, 
		0.0, scheme, DARK, 1.0)
	cairo_pattern_add_color_stop(linear_blend, 
		1.0, scheme, MEDIUM, 1.0)
	cr.set_source(linear_blend)
	cr.set_line_width(1.0)
	cr.stroke()

def paint_rounded_rect(cr, scheme, bounds, rx, ry, direction):
	# Firstly, round our bounds to an integer boundary
	int_bounds = boundsutils.align_to_integer_boundary(bounds)

	cr.new_path()

	# The inner part.
	rect_bounds = boundsutils.inset(int_bounds, 1, 1)
	cairoutils.rounded_rect(cr, rect_bounds, rx-1, ry-1)

	linear_blend = cairo.LinearGradient(
		rect_bounds.x1, rect_bounds.y1, 
		rect_bounds.x1, rect_bounds.y2)

	cairo_pattern_add_color_stop(linear_blend, 
		0.0, scheme, DARK, 1.0)
	cairo_pattern_add_color_stop(linear_blend, 
		0.33, scheme, MEDIUM, 1.0)
	cairo_pattern_add_color_stop(linear_blend, 
		1.0, scheme, LIGHT, 1.0)

	cr.set_source(linear_blend)
	cr.set_line_width(0.0)
	cr.fill_preserve()

	# The inner rectangle is a gradient from light to mid and 2px thick
	linear_blend = cairo.LinearGradient(
		rect_bounds.x1, rect_bounds.y1, 
		rect_bounds.x2, rect_bounds.y2)

	if(direction == IN):
		cairo_pattern_add_color_stop(linear_blend, 
			0.0, scheme, LIGHT, 1.0)
		cairo_pattern_add_color_stop(linear_blend,
			1.0, scheme, MEDIUM, 1.0)
	else:
		cairo_pattern_add_color_stop(linear_blend, 
			0.0, scheme, MEDIUM, 1.0)
		cairo_pattern_add_color_stop(linear_blend,
			1.0, scheme, LIGHT, 1.0)

	cr.set_line_width(2.0)
	cr.set_source(linear_blend)
	cr.stroke()

	# The outer rectangle is dark and 1px thick
	cr.set_line_width(1.0)
	cairo_set_source(cr, scheme, DARK)
	cairoutils.rounded_rect(cr, 
		boundsutils.inset(int_bounds, 0.5, 0.5), rx-0.5, ry-0.5)
	cr.stroke()

	# return the interior bounds
	interior_bounds = boundsutils.inset(int_bounds, 2.0, 2.0)
	return interior_bounds

# The Tango palette
_tango_palette = {
	#	NAME			LIGHT			MEDIUM			DARK			CONTRAST FLAGS[*]
	'Butter':			((252,233,79), 	(237,212,0),	(196,160,0), 	(0,0,1)),
	'Chameleon':		((138,226,52), 	(115,210,22),	(78,154,6),		(0,0,1)),
	'Orange':			((252,175,62),	(245,121,0),	(206,92,0), 	(0,1,1)),
	'Sky Blue':			((114,159,207),	(52,101,164),	(32,74,135), 	(0,1,1)),
	'Plum':				((173,127,168),	(117,80,123),	(92,53,102), 	(1,1,1)),
	'Chocolate':		((233,185,110),	(193,125,17),	(143,89,2),	 	(0,1,1)),
	'Scarlet Red':		((239,41,41),	(204,0,0),		(164,0,0), 		(1,1,1)),
	'Light Aluminium':	((238,238,236),	(211,215,207),	(186,189,182), 	(0,0,0)),
	'Dark Aluminium':	((136,138,133),	(85,87,83),		(46,52,54), 	(1,1,1)),

	# [*] (l,m,d) where {l,m,d} is 0 for black and 1 for white contrasting with
	#					{light, medium, dark}
}

# vim:sw=4:ts=4:autoindent
