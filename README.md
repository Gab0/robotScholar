## About

This is a tool to fetch the content of a list of articles as PMC IDs (pubmed), parse them using the [reach](https://github.com/clulab/reach) preprocessor wrapped here by the [Indra](https://github.com/sorgerlab/indra) python module.

Then a list of biological entities and processes are viewable on a webserver.

Not every article on pubmed is parseable for us, though. They must have an obtainable `.nxml`, and some articles, like closed-access papers or very old ones does not have them. Succes rate is about `33%`.

## Install

Clone the repo, cd its directory and run:

`$pip install .`

## Usage

There are two scrpts, usable as follows:

`$rsparse -d <output directory> -p <pmc_id list as .txt>`

`$rsview <output directory from rsparse>`

This tool can help you to get a list of PMC ids: [pmcc](https://github.com/Gab0/pmcrawl)
