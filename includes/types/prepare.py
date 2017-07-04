#!/usr/bin/env python
# coding: utf8

import csv
import os
import pickle
import sys

from gensim import corpora

from nltk.tokenize import PunktSentenceTokenizer, RegexpTokenizer
from stop_words import get_stop_words

from sklearn.feature_extraction.text import TfidfVectorizer
from slugify import slugify

def tokenize_content(file_to_content, de_stop, custom_stoplist=[], add_stoplist=[], token_min_length=0):
    """ Tokenize content using different stoplists and tokenizers """

    """
    You may use sterms, but its not recommended unless you know what you are doing.
    Consider taking a look at the docs.
    """
    #from nltk.stem.porter import PorterStemmer
    #from nltk.stem.snowball import SnowballStemmer
    #p_stemmer = PorterStemmer()
    #s_stemmer = SnowballStemmer("german")

    terms = []
    # load input data and parse every line/text -> tokens
    with open(file_to_content, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in reader:
            # makes content lowercase
            document = row[1].lower()

            # Split doc content into terms/words
            tokens = RegexpTokenizer('\w+').tokenize(document)

            # If you need stemmers, remove comments
            #tokens = [p_stemmer.stem(token) for token in tokens]
            #tokens = [s_stemmer.stem(token) for token in tokens]

            # include term only, when not in de_stop list
            tokens = [token for token in tokens if not token in de_stop]

            # include term only, when not in custom_stoplist
            tokens = [token for token in tokens if not token in custom_stoplist]

            # include term only, when not in add_stoplist
            tokens = [token for token in tokens if not token in add_stoplist]

            # include term ony, when length bigger than min_length
            tokens = [token for token in tokens if len(token) > token_min_length]

            # You can use this to remove digit-only terms
            #tokens = [token for token in tokens if not token.isdigit()]

            terms.append(tokens)

    return terms


def init_prepare():
    """ Initialize content preparation """

    try:
        sys.argv[2]
    except IndexError:
        print("Tool needs an argument - second argument (search query) non existent.")
        sys.exit()

    query = sys.argv[2]
    slug = slugify(query)

    base_path = os.path.abspath(
        os.path.dirname(
            sys.modules['__main__'].__file__
        )
    )

    save_path = base_path + "/data/csv/" + slug + "/"
    save_path_models = base_path + "/data//models/" + slug + "/dict/"
    statics_path = base_path + "/data/statics/"
    file_to_content = save_path + "content.csv"

    # create dict dir if not existent
    if not os.path.exists(save_path_models):
        os.makedirs(save_path_models)

    # load custom wordlist from file
    custom_stoplist = []

    with open(statics_path + "german-stopwords.txt", 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in reader:
            custom_stoplist.extend(row)

    # load additional stopwords from file
    add_stoplist = []

    with open(statics_path + "additionalwords.txt", 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in reader:
            add_stoplist.extend(row)

    # load standard german stoplist
    de_stop = get_stop_words('de')

    # set min length for tokens/terms (aka "Wörter")
    token_min_length = sys.argv[3] if len(sys.argv) >= 4 else 3
    token_min_length = int(token_min_length)

    """
    Part 1: Prepare input data/content for gensim ml algorithms
    """

    # get tokens/terms
    terms = tokenize_content(
        file_to_content=file_to_content,
        de_stop=de_stop,
        custom_stoplist=custom_stoplist,
        add_stoplist=add_stoplist,
        token_min_length=token_min_length
    )

    # create dictionary and save for future use
    dictionary = corpora.Dictionary(terms)
    dictionary.save(save_path_models + "dictionary.dict")

    # create corpus and save for future use
    corpus = [dictionary.doc2bow(term) for term in terms]
    corpora.MmCorpus.serialize(save_path_models + "corpus.mm", corpus)

    """
    Part 2: Prepare data/content for some sklearn ml algorithms
    """

    # concatenate stoplists
    stopword_lists = de_stop + custom_stoplist + add_stoplist

    # use sklearns tfidf vecotrizer
    tfidf_vectorizer = TfidfVectorizer(
        max_df=0.95,
        min_df=2,
        max_features=100,
        stop_words=stopword_lists
    )

    # tokenize senctences using PunktSentenceTokenizer
    sentences = []

    with open(file_to_content, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in reader:
            document = row[1].lower()
            tokens = PunktSentenceTokenizer().tokenize(document)
            for sent in tokens:
                sentences.append(sent)

    # transform tokens into tf idf matric
    tfidf_tokens = tfidf_vectorizer.fit_transform(sentences)

    # save tokens for future use
    pickle.dump(tfidf_tokens, open(save_path_models + "tfidf-tokens.sk", "wb"))

    # save this vectorizer for future use
    pickle.dump(tfidf_vectorizer, open(save_path_models + "tfidf-vectorizer.sk", "wb"))
