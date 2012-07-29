import logging
from pyjamas.ui.FlowPanel import FlowPanel
from pyjamas.ui.ScrollPanel import ScrollPanel
from pyjamas.ui.ToggleButton import ToggleButton

console = logging.getLogger()

class HorizontalCollapsePanel(FlowPanel):
    def __init__(self, *args, **kwargs):
        # set defaults
        if not 'StyleName' in kwargs:
            kwargs['StyleName'] = "rjw-HorizontalCollapsePanel"

        FlowPanel.__init__(self, *args, **kwargs)

        self._containers = [
                ScrollPanel(StyleName = self.getStylePrimaryName() + '-left'),
                ScrollPanel(StyleName = self.getStylePrimaryName() + '-right'),
        ]
        self._collapse_widget = ScrollPanel(StyleName = self.getStylePrimaryName() + '-collapse')
        collapse_button = ToggleButton(StyleName = self.getStylePrimaryName() + '-collapse-button')
        collapse_button.addClickListener(self._sync_collapse)
        self._collapse_widget.add(collapse_button)

        FlowPanel.add(self, self._containers[0])
        FlowPanel.add(self, self._collapse_widget)
        FlowPanel.add(self, self._containers[1])

        self._sync_collapse()

    def _sync_collapse(self, w=None):
        collapse_button = self._collapse_widget.getWidget(0)
        if collapse_button.isDown():
            self.addStyleName(self.getStylePrimaryName() + '-collapsed')
        else:
            self.removeStyleName(self.getStylePrimaryName() + '-collapsed')

    def getWidget(self, index):
        if index >= 0 and index < len(self._containers):
            return self._containers[index].getWidget()
        console.error('HorizontalCollapsePanel.getWidget passed invalid index: ' + str(index))
        raise IndexError('Index out of range')

    def setWidget(self, index, widget):
        if index >= 0 and index < len(self._containers):
            return self._containers[index].setWidget(widget)
        console.error('HorizontalCollapsePanel.setWidget passed invalid index: ' + str(index))
        raise IndexError('Index out of range')

    # Adds a widget to a pane
    def add(self, widget):
        if self.getWidget(0) == None:
            self.setWidget(0, widget)
        elif self.getWidget(1) == None:
            self.setWidget(1, widget)
        else:
            console.error("HorizontalCollapsePanel can only contain two child widgets.")

    # Removes a child widget.
    def remove(self, widget):
        if self.getWidget(0) == widget:
            self._containers[0].remove(widget)
        elif self.getWidget(1) == widget:
            self._containers[1].remove(widget)
        else:
            AbsolutePanel.remove(self, widget)

