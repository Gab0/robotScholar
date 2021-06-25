#!/bin/python


from . import fromReach, Network

import os

import argparse
import json


def validateNode(node):
    if len(node.split(" ")) > 5:
        return False
    else:
        return True


def relationshipsToNodes(Relationships, Entities):

    Nodes = []

    NodeNames = list(set([Node for Node in Entities if validateNode(Node)]))

    Sources = [r[0] for r in Relationships]
    Targets = [r[1] for r in Relationships]

    for s in list(set(Sources + Targets)):
        if validateNode(s):
            Nodes.append(Network.Vertex(s))

    for Source, Target, Level in Relationships:
        if Source in NodeNames and Target in NodeNames:
            for Node in Nodes:
                if Node.name == Source:
                    SourceNode = Node
                    break

            if Level > 0:
                SourceNode.upregulate.append(Target)
            else:
                SourceNode.downregulate.append(Target)

    return Nodes


def executeArticle(Relationships, Entities):
    if not Relationships:
        print("No relationships found.")
        return None

    if False:
        with open(fp+'R', 'w') as ft:
            wRelationships = [str(r) for r in Relationships]
            ft.write("\n".join(wRelationships))

    Nodes = relationshipsToNodes(Relationships, Entities)

    if False:
        with open(fp + "N", 'w') as ft:
            json.dump([N.toJson() for N in Nodes], ft, indent=4)

    return Nodes


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--dir", dest="OutputDirectory")
    parser.add_argument("-1", dest="OnePlot", action="store_true")

    options = parser.parse_args()
    Dir = options.OutputDirectory

    allRelationships, allEntities = [], []
    if Dir:
        allFiles = [f for f in os.listdir(Dir) if f.endswith(".json")]
        for i, F in enumerate(allFiles):
            fp = os.path.join(Dir, F)
            print("Processing %s\t(%i/%i)\n" % (fp, i + 1, len(allFiles)))

            Relationships, Entities = fromReach.processArticleJson(fp)
            if options.OnePlot:
                allRelationships += Relationships 
                allEntities += Entities
            if not options.OnePlot:
                Nodes = executeArticle(Relationships, Entities)

                outputFile = os.path.split(fp)[-1] + "_g.png"
                outputPath = os.path.join("networks", outputFile)
                Network.makeFigure(Nodes, fpath=outputPath)

        if options.OnePlot:
            allNodes = relationshipsToNodes(allRelationships, allEntities)
            outputPath = os.path.join("networks", os.path.split(Dir)[-1] + ".png")
            Network.makeFigure(allNodes, fpath=outputPath)
