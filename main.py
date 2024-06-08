# Honestly, some of the more janky code I've ever written
# I might clean it up later

import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox
from matplotlib.widgets import Button
from matplotlib.widgets import RadioButtons
import networkx as nx
import re

import netgraph as ng

# create network and plot
fig, ax = plt.subplots()

G = nx.DiGraph()
distinguished_center = 'Z'

# Used for selected edge
prev_edge = None
edge_color_default = 'black'
edge_color_selected = 'red'

# Re-draw the entire graph
plot_instance = None
artist_to_edge = {}
node_layout = None
def refresh(G):
    global plot_instance
    global artist_to_edge

    ax.clear()

    edge_labels = {(u, v): label for (u, v, label) in G.edges(data="label", default="")}

    plot_instance = ng.InteractiveGraph(G, ax=ax,
                          node_size=5, node_labels=True,
                          edge_width=2.5, edge_labels=edge_labels, edge_label_rotate=False,
                          edge_color=edge_color_default, edge_label_position=0.70,
                          arrows=True, node_layout=node_layout)

    # make edge artists pickable and map each edge artist to the corresponding string
    artist_to_edge = {}
    for edge, artist in plot_instance.edge_artists.items():
        artist.set_picker(True)
        artist_to_edge[artist] = edge

    fig.canvas.mpl_connect('pick_event', on_pick)
    fig.canvas.draw()

# Unfortunately, netgraph does not support MultiGraph and MultiDiGraph
# Hence, we will simulate it with single edges and labels that "contain"
# multiple edges, ex: label="a,b,c"
def add_multiedge(G, u, v, label):
    if (u,v) in G.edges():
        G.edges[u,v]["label"] += "," + label
    else:
        G.add_edge(u, v, label=label)

# Remove duplicate edges from a single label
def remove_duplicate_edges(str):
    return ','.join(sorted(list(set(str.split(',')))))

# Code for selecting edges
def on_pick(event):
    global prev_edge
    global G

    edge = artist_to_edge[event.artist]

    # Nothing currently selected
    # Keep track and highlight it as red
    if prev_edge is None:
        prev_edge = edge
        plot_instance.edge_artists[edge].set_facecolor(edge_color_selected)
        fig.canvas.draw()
        return

    # Clicked on already selected edge
    # Undo everything
    if prev_edge == edge:

        # Can be used to remove multiple copies of the same edge,
        # but kind of annoying because this solution refreshes the whole graph
        #G.edges[edge]["label"] = ','.join(sorted(list(set(G.edges[edge]["label"].split(',')))))
        #refresh(G)

        prev_edge = None
        plot_instance.edge_artists[edge].set_facecolor(edge_color_default)
        fig.canvas.draw()
        return

    # One edge already selected, clicked on another
    # Check if valid Stalling fold is possible.
    if prev_edge is not None and prev_edge != edge:

        prev_multiedge = G.edges[prev_edge]["label"].split(',')
        curr_multiedge = G.edges[edge]["label"].split(',')

        # Fold is only possible if they have the same label to begin with
        if set(prev_multiedge).isdisjoint(set(curr_multiedge)):
            return

        # We will merge the "old" node into the "new" node
        merge_old = 0
        merge_new = 0

        # Same source. Basically, anything with range of edge[1]
        # will be changed to have range of prev_edge[1]
        if prev_edge[0] == edge[0]:
            merge_old = prev_edge[1]
            merge_new = edge[1]
        # Same range instead. Anything with source of edge[0]
        # will be changed to have source of prev_edge[0]
        elif prev_edge[1] == edge[1]:
            merge_old = prev_edge[0]
            merge_new = edge[0]
        else: # This shouldn't happen
            print("Incompatible edges")
            return

        # Preserve the distinguished node
        if merge_old == distinguished_center:
            merge_old = merge_new
            merge_new = distinguished_center

        # Actually refresh the entire drawing, and reset selection
        prev_edge = None
        G_new = nx.DiGraph()
        for old_edge in G.edges():
            add_multiedge(G_new,
                          merge_new if old_edge[0] == merge_old else old_edge[0],
                          merge_new if old_edge[1] == merge_old else old_edge[1],
                          label=G.edges[old_edge]["label"])

        # Remove duplicate edges
        for new_edge in G_new.edges():
            G_new.edges[new_edge]["label"] = remove_duplicate_edges(G_new.edges[new_edge]["label"])

        G = G_new
        refresh(G)

# Assuming an element of the form a^2b^{-1}ab^{-2}
# is represented as aab-ab-b-
# Also distinguish between nodes coming from different elements
# with element n giving n,1 and n,2 and ...
def add_group_element(G, element, n):
    generators = re.findall("[a-z]-?", element)

    for i in range(0,len(generators)):
        src = str(n) + ',' + str(i)
        ran  = str(n) + ',' + str(i+1)

        # Edge cases (literally)
        if i == 0:
            src = distinguished_center

        if i == len(generators) - 1:
            ran = distinguished_center

        # If the element is negative, backwards arrow
        if len(generators[i]) == 2:
            temp = ran
            ran = src
            src = temp

        add_multiedge(G, src, ran, generators[i][0])

# When the "refresh" button is clicked
def on_refresh(arg):
    global node_layout
    global prev_edge

    prev_edge = None

    match radio_style.value_selected:
        case 'Planar':
            node_layout = nx.planar_layout(G)
        case 'Shell':
            node_layout = nx.shell_layout(G)
        case 'Random':
            node_layout = nx.random_layout(G)

    refresh(G)

# When the group elements are specified
def on_textinput(input):
    global G

    elements = re.findall("[a-z\-]+", input)

    G = nx.DiGraph()

    for i in range(0, len(elements)):
        add_group_element(G, elements[i], i)

    on_refresh(None)

# When the restart button is clicked, same as entering group elements
def on_restart(arg):
    on_textinput(text_box.text)

# Actually create all components of the window here.
#
# Radio buttons to select style
# Text box to enter group elements
# Button to refresh the graph
# Button to restart (recreate the graph from the beginning)
#
ax_style = fig.add_axes([0.05, 0.8, 0.15, 0.15])
radio_style = RadioButtons(ax_style, labels=('Shell', 'Planar', 'Random'))

ax_box = fig.add_axes([0.2, 0.05, 0.7, 0.075])
text_box = TextBox(ax_box, "Elements", textalignment="center")
text_box.on_submit(on_textinput)

# This actually initializes the first drawing of the graph
text_box.set_val("aab-, aaab, a-bb, aba, aaab-b-a-")

ax_refresh = fig.add_axes([0.8, 0.9, 0.1, 0.05])
ax_restart = fig.add_axes([0.8, 0.84, 0.1, 0.05])

b_refresh = Button(ax_refresh, 'Refresh')
b_refresh.on_clicked(on_refresh)

b_restart = Button(ax_restart, 'Restart')
b_restart.on_clicked(on_restart)

plt.show()