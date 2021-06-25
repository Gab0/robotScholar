#!/bin/python
import math
import igraph


def hex2color(Hex):
    return [
        int(Hex[i: i + 2], 16)
        for i in range(0, 6, 2)
    ]


def color2hex(Color):
    c = [
        hex(round(c))[2:] for c in Color
    ]
    return "".join(c)


def mergeColors(A, B):
    [A, B] = [hex2color(x) for x in [A, B]]

    HexColor = [(A[i] + B[i]) / 2 for i in range(len(A))]

    return color2hex(HexColor)


class Vertex():
    def __init__(self, name,
                 descr=None,
                 upregulate=None,
                 downregulate=None,
                 Type=None,
                 colorScheme=None):

        self.description = descr
        self.name = name

        # Using None instead of plain [] because of strange bug(?).
        self.Type = Type if Type else []
        self.upregulate = upregulate if upregulate else []
        self.downregulate = downregulate if downregulate else[]

        self.colorScheme = colorScheme if colorScheme else [
            "#67a9cf",
            "#7fcdbb",
            "#fa9fb5",
            "#6cccfc",
        ]

    def V(self, G, TypeDefinitions):

        if self.Type:
            color = TypeDefinitions[self.Type[0]]
        else:
            color = ["#ffffff", "#000000"]

        G.add_vertex(
            self.name,
            size=max(50, len(self.name) * 9),
            color=color[0],
            label_color=color[1]
        )

    def E(self, G):
        for tgt in self.upregulate:
            G.add_edge(self.name, tgt, color="#177017")

        for tgt in self.downregulate:
            G.add_edge(self.name, tgt, color="red")

    def toJson(self):
        return {
            "name": self.name,
            "upregulate": self.upregulate,
            "downregulate": self.downregulate,
            "Type": self.Type
        }


def makeFigure(Nodes,
               fpath=None,
               cluster=None,
               layoutArguments={},
               TypeDefinitions={},
               PlotSize=None):

    G = igraph.Graph(directed=True)
    Vertices = [n.name for n in Nodes]

    for n in Nodes:
        n.V(G, TypeDefinitions)

    for n in Nodes:
        try:
            for V in n.upregulate + n.downregulate:
                # Some target entities are not listed as
                # initial entities from article from reach tree data;
                if V not in Vertices:
                    Vtx = Vertex(V)
                    Nodes.append(Vtx)
                    Vertices.append(V)
                    Vtx.V(G, TypeDefinitions)

            n.E(G)

        except Exception as e:
            print("Failure.")
            print(e)
            print(n.upregulate)
            print(n.downregulate)
            print(Vertices)
            exit()

    if not PlotSize:
        PlotSize = len(Nodes) ** 4 * 6

    PlotSide = round(math.sqrt(PlotSize))

    # Vertex Attributes;
    G.vs["user_name"] = Vertices
    style = {}
    style["edge_curved"] = True
    style["margin"] = 100
    style["vertex_label"] = G.vs["user_name"]
    style["vertex_label_cex"] = 0.4
    style["vertex_label_angle"] = math.pi / 2
    style["bbox"] = (PlotSide, PlotSide)

    # print(G.modularity(cluster))

    Layouts = [
        "kamada_kawai",
        "fr"
    ]
    if not layoutArguments:
        layoutArguments = {
            "layout": Layouts[0]
        }

    layout = G.layout(**layoutArguments)

    print(f"Writing graph to {fpath}.")

    return igraph.plot(G, target=fpath, layout=layout, **style)
