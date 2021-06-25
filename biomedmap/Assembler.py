#!/bin/python

import json
import indra.assemblers.index_card.assembler as idxc


def getIndexCards(Statements):
    Cards = idxc.IndexCardAssembler(statements=Statements)

    Cards.make_model()

    data = Cards.print_model()

    return data


if __name__ == "__main__":
    data = json.load(open("/home/gabs/scholar_articles/BGRA/PMC2132784.json"))
    getIndexCards(data["events"]["frames"])
