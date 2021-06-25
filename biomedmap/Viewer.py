#!/bin/python

import os
import sys
import json

import argparse
import time
import datetime

import re
import base64
import tempfile

from flask import Flask, render_template

import spacy
import waitress

from . import Networks


class SentenceData():
    """

    Holds a sentence and its related attributes.

    """
    def __init__(self):
        pass

    def fromJson(self, obj):
        self.sentence = obj["sentence"]
        self.highlight = obj["highlight"]
        self.source = obj["source"]
        self.entity = obj["entity"]
        self.score = obj["score"]
        return self

    def getText(self):
        w = self.sentence.split(self.highlight)
        sentence = [
            w[0],
            self.highlight,
            w[1]
        ]

        return sentence

    def toJson(self):
        obj = {
            "sentence": self.sentence,
            "highlight": self.highlight,
            "source": self.source,
            "entity": self.entity,
            "score": 0
        }
        return obj

    def __eq__(self, ot):
        return self.sentence == ot.sentence

    def __hash__(self):
        content = self.sentence + self.source
        return sum([ord(c) for c in content])


class IndraViewer():
    def __init__(self, datadir):
        app = Flask(__name__, template_folder="templates")

        self.nlp = spacy.load("en_core_web_sm")

        @app.route("/")
        @app.route("/<viewMode>")
        @app.route("/<viewMode>/<selectedEntity>")
        def showIndex(selectedEntity=None, viewMode="global"):
            return render_template(
                "viewer.html",
                content=self.content,
                selectedEntity=selectedEntity,
                viewMode=viewMode,
                searchName=datadir
            )

        @app.route("/graph/<datadir>/<article_file>")
        def showGraph(datadir=None, article_file=None):
            if article_file:
                articleData = os.path.join(datadir, article_file)
                Relationships, Entities =\
                    Networks.fromReach.processArticleJson(articleData)
                Nodes = Networks.ParseArticles.executeArticle(
                    Relationships,
                    Entities
                )
                if Nodes is not None:
                    self.log("Building graph...")

                    # Create temporary file...
                    # seems the only way possible with currently broken
                    # jgraph.plot._repr_svg_
                    F = tempfile.mkstemp(prefix="graph", suffix=".png")
                    Networks.Network.makeFigure(Nodes, fpath=F[1])

                    data = open(F[1], 'rb').read()
                    data = base64.b64encode(data).decode("utf-8")

                    os.unlink(F[1])
                    self.log("Serving graph...")
                    return render_template(
                        "graph.html", graphdata=data
                    )
                else:
                    return ('', 204)

        dataFilePath = "%s.json" % datadir

        if not os.path.isfile(dataFilePath):
            self.content = self.process_data(datadir)
            json.dump(self.content,
                      open(dataFilePath, 'w'),
                      indent=2)
        else:
            self.log("Reading %s..." % dataFilePath)

            self.content = json.load(open(dataFilePath))

        self.log("Rebuilding sentence objects...")
        self.content["EntitiesSentences"] = [
            [
                SentenceData().fromJson(p)
                for p in l
            ]
            for l in self.content["EntitiesSentences"]
        ]

        for A, Article in enumerate(self.content["ArticleData"]):
            Article["articleSentences"] = [
                SentenceData().fromJson(p)
                for p in Article["articleSentences"]
            ]

        ArticleSentencesCount = sum([
            len(Article["articleSentences"])
            for Article in self.content["ArticleData"]
        ])

        self.log("Found %i article sentences." % ArticleSentencesCount)
        self.log("Done.")
        self.app = app

    def log(self, message):
        t = datetime.datetime.now().strftime("%H:%M:%S")
        print("[ %s ] %s\n" % (t, message))

    def findMatchingEntities(self, content):
        matchedEntities = []

        for c, C in enumerate(content):
            matchedEntities += [
                ent[0] for ent in C['entities']
            ]

        matchedEntities = sorted(list(set(matchedEntities)))

        if True:
            for i, iEntity in enumerate(matchedEntities):
                if iEntity is None:
                    continue
                for j, jEntity in enumerate(matchedEntities):
                    if i == j or jEntity is None:
                        continue

                    if re.findall("^%s " % re.escape(iEntity), jEntity):
                        matchedEntities[j] = None

            matchedEntities = list(filter(None, matchedEntities))

        return matchedEntities

    def extract_entity_sentences(self, ArticleData, Entity):
        Sentences = []

        for a, Article in enumerate(ArticleData):
            for Sentence in Article["sentences"]:
                if Entity.lower() in Sentence.lower():
                    for Event, Score in Article["events"]:
                        if Event in Sentence:
                            s = {
                                "source": Article["ID"],
                                "sentence": Sentence,
                                "highlight": Event,
                                "entity": Entity,
                                "score": 0
                                }

                            Sentences.append(s)
                            break
        return Sentences

    def process_data(self, datadir):

        self.log("Loading Article Data at %s." % datadir)
        time0 = time.time()

        self.articleFilenames = os.listdir(datadir)
        self.articleFilepaths = [
            os.path.join(datadir, f)
            for f in self.articleFilenames
        ]

        ArticleData = [
            self.load_json(f)
            for f in self.articleFilepaths
        ]

        ArticleData = list(filter(None, ArticleData))

        self.log("\nLocating matching entities...")

        matchedEntities = self.findMatchingEntities(ArticleData)

        self.log("\nLocating events that match entities...")

        EntitiesSentences = []

        step = len(matchedEntities) // 10
        for e, Entity in enumerate(matchedEntities):
            Sentences = self.extract_entity_sentences(ArticleData, Entity)

            # Sentences = list(set(Sentences))

            EntitiesSentences.append(Sentences)

            if not e % step:
                print("%.2f%%" % (100 * (e+1) / len(matchedEntities)))

        # ERASE EMPTY matchedEntities
        matchedEntities = [
            MatchedEntity
            for e, MatchedEntity in enumerate(matchedEntities)
            if EntitiesSentences[e]
        ]

        # ERASE EMPTY EntitiesSentences
        EntitiesSentences = [
            e
            for e in EntitiesSentences if e
        ]

        # print(self.matchedEntitiesEvents)
        print("%.2f seconds to process data." % (time.time() - time0))

        content = {
            "content": ArticleData,
            "matchedEntities": matchedEntities,
            "EntitiesSentences": EntitiesSentences,
            "ArticleData": ArticleData
        }

        return content

    def load_json(self, jsonFile):
        try:
            content = json.load(open(jsonFile))
        except json.decoder.JSONDecodeError:
            return None

        if isinstance(content, list):
            self.log("Converting list[%i] to dict." % len(content))
            if len(content) == 0:
                self.log("Empty content at %s" % jsonFile)
                return None
            content = content[0]

        ArticleID = os.path.split(jsonFile)[-1].split(".")[0]
        outputContent = {
            "ID": ArticleID,
            "name": jsonFile,
            "Title": content["Title"],
            "events": content["events"]["frames"],
            "entities": content["entities"]["frames"],
            "sentences": content["sentences"]["frames"]
        }

        def extractText(l):
            return [
                clean_sentence(c["text"])
                for c in l
            ]

        allEvents = extractText(outputContent["events"])
        allEntities = extractText(outputContent["entities"])
        allSentences = extractText(outputContent["sentences"])[1:]

        allEntities = list(set(allEntities))

        outputEvents = [
            self.validate_phrase(phrase)
            for phrase in allEvents
        ]

        outputEntities = [(p, 0) for p in allEntities]

        outputContent["events"] = outputEvents
        outputContent["entities"] = sorted(outputEntities)
        outputContent["sentences"] = allSentences

        ArticleSentences = []
        for Event, Score in outputContent["events"]:
            for Sentence in outputContent["sentences"]:
                if Event in Sentence:
                    sentence_data = {
                        "sentence": Sentence,
                        "highlight": Event,
                        "source": outputContent["ID"],
                        "keyword": None,
                        "entity": None,
                        "score": 0
                    }

                    ArticleSentences.append(sentence_data)
                    break

        outputContent["articleSentences"] = ArticleSentences

        return outputContent

    def validate_phrase(self, phrase):
        score = 0
        doc = self.nlp(phrase)
        Verbs = [
            token.lemma_
            for token in doc
            if token.pos_ == "VERB"
        ]
        if Verbs:
            score = 1

        return (phrase, score)


def clean_sentence_xref(sentence):
    pattern = r" *[\[\()]+.*%s.*[\]\)] *"
    contents = ["XREF_BIBR", "XREF_FIG"]

    for content in contents:
        sentence = re.sub(pattern % content, "", sentence)

    return sentence


def clean_sentence(sentence):
    actions = [
        clean_sentence_xref
    ]

    for action in actions:
        sentence = action(sentence)

    return sentence


def parse_arguments(parser=argparse.ArgumentParser()):
    parser.add_argument(dest="InputDirectory")
    parser.add_argument("-p", "--port", type=int, default=5000)
    return parser


def main():
    execute(parse_arguments().parse_args())


def execute(arguments):

    Viewer = IndraViewer(arguments.InputDirectory)
    waitress.serve(Viewer.app, port=arguments.port)




if __name__ == "__main__":
    main()
