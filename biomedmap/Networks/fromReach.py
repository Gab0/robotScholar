#!/bin/python

import json


def processArticleJson(filepath):
    Data = json.load(open(filepath))

    Frames = Data["events"]["frames"]

    ArgumentTypes = [
        "controller",
        "controlled"
    ]

    Activations = {
        "positive-activation": 1,
        "positive-regulation": 1,
        "negative-activation": -1,
        "negative-regulation": -1
    }

    Relationships = []
    for Frame in Frames:
        Arguments = Frame["arguments"]
        Entities = [None, None]
        if len(Arguments) > 1:
            for Argument in Arguments:
                Type = Argument["type"]
                if Type in ArgumentTypes:
                    Index = ArgumentTypes.index(Type)

                    Entities[Index] = Argument["text"]

            if all(Entities):
                Signal = Activations[Frame["subtype"]]
                Relationships.append((*Entities, Signal))

    Entities = [e["text"] for e in Data["entities"]["frames"]]
    return Relationships, Entities
