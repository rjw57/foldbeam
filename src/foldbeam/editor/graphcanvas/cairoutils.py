import cairo
import math

import boundsutils

def rounded_rect(cr, bounds, radiusx, radiusy):
	cr.new_path()

	(x,y,width,height) = boundsutils.to_rect(bounds)
	if((radiusx <= 0.0) or (radiusy <= 0.0)):
		cr.rectangle(x,y,width,height)
		return
	
	# == If we get here, we need to do a rounded rectangle. ==

	# The radii can't be more than half the size of the rect. 
	rx = min(radiusx, 0.5*width)
	ry = min(radiusy, 0.5*height)

	# Draw top-right arc
	cr.save()
	cr.translate(bounds.x2 - rx, bounds.y1 + ry)
	cr.scale(rx, ry)
	cr.arc(0.0, 0.0, 1.0, 1.5 * math.pi, 2.0 * math.pi)
	cr.restore()

	# Draw the line down the right side. 
	cr.line_to(bounds.x2, bounds.y2 - ry)
	
	# Draw the bottom-right arc. 
	cr.save()
	cr.translate(bounds.x2 - rx, bounds.y2 - ry)
	cr.scale(rx, ry)
	cr.arc(0.0, 0.0, 1.0, 0.0, 0.5 * math.pi)
	cr.restore()

	# Draw the line left across the bottom. 
	cr.line_to(bounds.x1 + rx, bounds.y2)

	# Draw the bottom-left arc. 
	cr.save()
	cr.translate(bounds.x1 + rx, bounds.y2 - ry)
	cr.scale(rx, ry)
	cr.arc(0.0, 0.0, 1.0, 0.5 * math.pi, math.pi)
	cr.restore()

	# Draw the line up the left side. 
	cr.line_to(bounds.x1, bounds.y1 + ry)
	
	# Draw the top-left arc. 
	cr.save()
	cr.translate(bounds.x1 + rx, bounds.y1 + ry)
	cr.scale(rx, ry)
	cr.arc(0.0, 0.0, 1.0, math.pi, 1.5 * math.pi)
	cr.restore()

	# Close the path accross the top.
	cr.close_path()

# vim:sw=4:ts=4:autoindent
