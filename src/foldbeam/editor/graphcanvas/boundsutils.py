import goocanvas
import math

def from_rect(*args):
	if(len(args) == 1):
		(x,y,width,height) = args[0]
	else:
		(x,y,width,height) = args
	return goocanvas.Bounds(x,y,x+width,y+height)

def do_intersect(bounds_a, bounds_b):
	# We test for intersection by testing for intersection
	# in X and Y separately. Each 1D test sees if one extremal
	# point from a bound is within the other.

	x_intersect = False
	if((bounds_a.x1 <= bounds_b.x1) and (bounds_a.x2 >= bounds_b.x1)):
		x_intersect = True
	elif((bounds_a.x1 <= bounds_b.x2) and (bounds_a.x2 >= bounds_b.x2)):
		x_intersect = True
	elif((bounds_b.x1 <= bounds_a.x1) and (bounds_b.x2 >= bounds_a.x1)):
		x_intersect = True
	elif((bounds_b.x1 <= bounds_a.x2) and (bounds_b.x2 >= bounds_a.x2)):
		x_intersect = True

	y_intersect = False
	if((bounds_a.y1 <= bounds_b.y1) and (bounds_a.y2 >= bounds_b.y1)):
		y_intersect = True
	elif((bounds_a.y1 <= bounds_b.y2) and (bounds_a.y2 >= bounds_b.y2)):
		y_intersect = True
	elif((bounds_b.y1 <= bounds_a.y1) and (bounds_b.y2 >= bounds_a.y1)):
		y_intersect = True
	elif((bounds_b.y1 <= bounds_a.y2) and (bounds_b.y2 >= bounds_a.y2)):
		y_intersect = True
	
	return (x_intersect and y_intersect)

def align_to_integer_boundary(bounds):
	out_bounds = goocanvas.Bounds(
		math.floor(bounds.x1),
		math.floor(bounds.y1),
		math.ceil(bounds.x2),
		math.ceil(bounds.y2))
	return out_bounds

def offset(bounds, dx, dy):
	out_bounds = goocanvas.Bounds(
		bounds.x1 + dx,
		bounds.y1 + dy,
		bounds.x2 + dx,
		bounds.y2 + dy)
	return out_bounds

def inset(bounds, dx, dy):
	out_bounds = goocanvas.Bounds(
		bounds.x1 + dx,
		bounds.y1 + dy,
		bounds.x2 - dx,
		bounds.y2 - dy)
	return out_bounds

def to_rect(bounds):
	return (bounds.x1, bounds.y1, bounds.x2-bounds.x1, bounds.y2-bounds.y1)

def get_size(bounds):
	return (bounds.x2-bounds.x1, bounds.y2-bounds.y1)

def contains_point(bounds, x, y):
	return ((bounds.x1 <= x) and (bounds.x2 >= x) and
		(bounds.y1 <= y) and (bounds.y2 >= y))

def describe(bounds):
	return '(%f,%f) -> (%f,%f)' % \
		(bounds.x1, bounds.y1, bounds.x2, bounds.y2)

# vim:sw=4:ts=4:autoindent
