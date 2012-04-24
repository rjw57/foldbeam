import tango
import boundsutils
import cairoutils
import goocanvas
import gobject
import simple
import node
import edge

class GraphItem(goocanvas.Group, simple.SimpleItem, goocanvas.Item):
	''' A GraphItem is a sub-class of a goocanvas Group which holds items 
	    relating to a graph. The main purpose of the sub-class is to implement
		methods which allow nodes and edges to communicate pad locations
		to one another. '''

	__gsignals__ = {
		'pad-anchor-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
			(gobject.TYPE_OBJECT, float, float)),
	}

	def __init__(self, *args, **kwargs):
		goocanvas.Group.__init__(self, *args, **kwargs)
		self._pad_anchors = { }
	
	def set_pad_anchor(self, pad_model, x, y):
		self._pad_anchors[pad_model] = (x,y)
		self.emit('pad-anchor-changed', pad_model, x, y)
	
	def get_pad_anchor(self, pad_model):
		return self._pad_anchors[pad_model]
	
	def set_model(self, model):
		goocanvas.Group.set_model(self, model)

gobject.type_register(GraphItem)

class GraphModel(goocanvas.GroupModel, goocanvas.ItemModel):
	''' A GraphModel holds a list of node models and edge models
		which collectively form a graph. 

		The GraphModel holds two 'sub group' models, one for nodes
		and one for edges. The edge group will always be atop the
		node group.
		'''

	__gsignals__ = {
		'node-added': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
			(gobject.TYPE_OBJECT,)),
		'edge-added': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
			(gobject.TYPE_OBJECT,)),
		'node-removed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
			(gobject.TYPE_OBJECT,)),
		'edge-removed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
			(gobject.TYPE_OBJECT,)),
	}

	def __init__(self, *args, **kwargs):
		goocanvas.GroupModel.__init__(self, *args, **kwargs)

		## add internal models for nodes and edges
		self._node_models = goocanvas.GroupModel(parent = self)
		self._edge_models = goocanvas.GroupModel(parent = self)

		## a list of canvases and the items we created on them
		self._canvas_item_map = { }
	
	## node manipulation
	def add_node(self, node_model, pos):
		if(not isinstance(node_model, node.NodeModel)):
			raise TypeError('node must be instance of NodeModel.')
		self.add_child(node_model, pos)
	
	def get_n_nodes(self):
		return self._node_models.get_n_children()
	
	def get_node(self, node_idx):
		return self._node_models.get_child(node_idx)
	
	def remove_node(self, node_idx):
		node = self.get_node(node_idx)
		if node is None:
			return

		# Remove any edges connected to this node.
		to_remove = []
		for i in range(0, self.get_n_edges()):
			edge = self.get_edge(i)
			start = edge.get_property('start-pad').get_property('parent')
			end = edge.get_property('end-pad').get_property('parent')
			if (start == node) or (end == node):
				to_remove.append(edge)

		for e in to_remove:
			self.remove_edge(self.find_edge(e))

		self.emit('node-removed', self.get_node(node_idx))
		return self._node_models.remove_child(node_idx)
	
	def move_node(self, old_idx, new_idx):
		return self._node_models.move_child(old_idx, new_idx)
	
	def find_node(self, node_model):
		if(not isinstance(node_model, node.NodeModel)):
			raise TypeError('node must be instance of NodeModel.')
		for idx in range(self.get_n_nodes()):
			if(self.get_node(idx) == node_model):
				return idx
		return -1
	
	## edge manipulation
	def add_edge(self, edge, pos):
		if(not isinstance(edge, edge.EdgeModel)):
			raise TypeError('edge must be instance of EdgeModel.')
		self.add_child(edge, pos)
	
	def get_n_edges(self):
		return self._edge_models.get_n_children()
	
	def get_edge(self, edge_idx):
		return self._edge_models.get_child(edge_idx)
	
	def remove_edge(self, edge_idx):
		self.emit('edge-removed', self.get_edge(edge_idx))
		return self._edge_models.remove_child(edge_idx)
	
	def move_edge(self, old_idx, new_idx):
		return self._edge_models.move_child(old_idx, new_idx)
	
	def find_edge(self, edge_model):
		if(not isinstance(edge_model, edge.EdgeModel)):
			raise TypeError('edge must be instance of EdgeModel.')
		for idx in range(self.get_n_edges()):
			if(self.get_edge(idx) == edge_model):
				return idx
		return -1
	
	## group methods
	def do_add_child(self, child, pos):
		## special cases for nodes and edges - essentially
		## we're creating a node and edge layer.
		if(isinstance(child, node.NodeModel)):
			self._node_models.add_child(child, pos)
			child.set_graph_model(self)
			self.emit('node-added', child)
		elif(isinstance(child, edge.EdgeModel)):
			self._edge_models.add_child(child, pos)
			self.emit('edge-added', child)
		else:
			goocanvas.GroupModel.do_add_child(self, child, pos)

	def _on_sub_item_created(self, canvas, item, model):
		''' When a sub-item is created, we retrieve the appropriate
		    graph item and call the 'set_graph_item' method on the new
			item if present. This allows edges to register their interest
			in pad anchor change events. '''

		## see if this item has a parent and if it is one
		## of our sub-groups
		if(item == None):
			return
		item_model = item.get_model()
		if(item_model == None):
			return
		item_parent = item_model.get_parent()
		if((item_parent != self._node_models) and (item_parent != self._edge_models)):
			return

		if(not hasattr(item, 'set_graph_item')):
			return

		item.set_graph_item(self._canvas_item_map[canvas])
	
	## item model methods
	def do_create_item(self, canvas):
		item = GraphItem()
		#item = goocanvas.Group()
		item.set_model(self)
		item.set_canvas(canvas)
		self._canvas_item_map[canvas] = item

		canvas.connect('item-created', self._on_sub_item_created)

		## for each child, create an item and add it
		for idx in range(self.get_n_children()):
			child = self.get_child(idx)

			## FIXME: Horrible hack
			try:
				item.add_child(child.do_create_item(canvas))
			except:
				item.add_child(child.do_create_item(child, canvas))

		return item

gobject.type_register(GraphModel)


# vim:sw=4:ts=4:autoindent
