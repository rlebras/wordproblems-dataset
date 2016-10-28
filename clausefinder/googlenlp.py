import collections
import os, sys, json, requests
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials

POS_LOOKUP = [
    'UNKNOWN',  # Unknown
    'ADJ',      # Adjective
    'ADP',	    # Adposition (preposition and postposition)
    'ADV',      # Adverb
    'CONJ',     # Conjunction
    'DET',      # Determiner
    'NOUN',     # Noun (common and proper)
    'NUM',	    # Cardinal number
    'PRON',     # Pronoun
    'PRT',	    # Particle or other function word
    'PUNCT',    # Punctuation
    'VERB',     # Verb (all tenses and modes)
    'X',        # Other: foreign words, typos, abbreviations
    'AFFIX'     # Affix
]

POS = { }
for v in range(len(POS_LOOKUP)):
    POS[ POS_LOOKUP[v] ] = v

PARSE_LABEL_LOOKUP = [
    'UNKNOWN',      # Unknown
    'ABBREV',       # Abbreviation modifier
    'ACOMP',        # Adjectival complement
    'ADVCL',        # Adverbial clause modifier
    'ADVMOD',	    # Adverbial modifier
    'ADVPHMOD',     # Adverbial phrase modifier
    'AMOD',         # Adjectival modifier of an NP
    'APPOS',        # Appositional modifier of an NP
    'ATTR',         # Attribute dependent of a copular verb
    'AUX',          # Auxiliary (non-main) verb
    'AUXPASS',	    # Passive auxiliary
    'AUXCAUS',      # Causative auxiliary
    'AUXVV',        # Helper auxiliary
    'CC',           # Coordinating conjunction
    'CCOMP',        # Clausal complement of a verb or adjective
    'CONJ',         # Conjunct
    'COP',          # Copula
    'CSUBJ',        # Clausal subject
    'CSUBJPASS',    # Clausal passive subject
    'DEP',          # Dependency (unable to determine)
    'DET',          # Determiner
    'DISCOURSE',    # Discourse
    'DISLOCATED',   # Dislocated relation (for fronted/topicalized elements)
    'DOBJ',         # Direct object
    'DTMOD',        # Rentaishi (Prenominal modifier)
    'EXPL',         # Expletive
    'FOREIGN',      # Foreign words
    'GOESWITH',     # Goes with (part of a word in a text not well edited)
    'IOBJ',         # Indirect object
    'KW',           # Keyword
    'LIST',         # List for chains of comparable items
    'MARK',         # Marker (word introducing a subordinate clause)
    'MWE',	        # Multi-word expression
    'MWV',	        # Multi-word verbal expression
    'NEG',          # Negation modifier
    'NN',           # Noun compound modifier
    'NOMC',         # Nominalized clause
    'NOMCSUBJ',     # Nominalized clausal subject
    'NOMCSUBJPASS', # Nominalized clausal passive
    'NUMC',         # Compound of numeric modifier
    'NPADVMOD',     # Noun phrase used as an adverbial modifier
    'NSUBJ',        # Nominal subject
    'NSUBJPASS',    # Passive nominal subject
    'NUM',          # Numeric modifier of a noun
    'NUMBER',       # Element of compound number
    'P',            # Punctuation mark
    'PARATAXIS',    # Parataxis relation
    'PARTMOD',      # Participial modifier
    'PCOMP',        # The complement of a preposition is a clause
    'POBJ',         # Object of a preposition
    'POSS',         # Possession modifier
    'POSTNEG',      # Postverbal negative particle
    'PRECOMP',      # Predicate complement
    'PRECONJ',      # Preconjunt
    'PREDET',       # Predeterminer
    'PREF',         # Prefix
    'PREP',         # Prepositional modifier
    'PRONL',        # The relationship between a verb and verbal morpheme
    'PRT',          # Particle
    'PS',           # Associative or possessive marker
    'QUANTMOD',     # Quantifier phrase modifier
    'RCMOD',        # Relative clause modifier
    'RCMODREL',     # Complementizer in relative clause
    'RDROP',        # Ellipsis without a preceding predicate
    'REF',          # Referent
    'REMNANT',      # Remnant
    'REPARANDUM',   # Reparandum
    'ROOT',         # Root
    'SNUM',         # Suffix specifying a unit of number
    'SUFF',         # Suffix
    'SUFFIX',       # Name suffix
    'TITLE',	    # Name title
    'TMOD',         # Temporal modifier
    'TOPIC',        # Topic marker
    'VMOD',         # Clause headed by an infinite form of the verb that modifies a noun
    'VOCATIVE',     # Vocative
    'XCOMP',        # Open clausal complement
]

PARSE_LABEL = { }
for v in range(len(PARSE_LABEL_LOOKUP)):
    PARSE_LABEL[ PARSE_LABEL_LOOKUP[v] ] = v


class DependencyTrees(object):
    '''Dependency Tree'''

    def __init__(self, nlpResult):
        self._sentences = nlpResult['sentences']
        self._tokens = nlpResult['tokens']
        self._trees = [ None ] * len(self._sentences)
        g = -1
        for tok in self._tokens:
            tok['adj'] = []
        i = 0
        for tok in self._tokens:
            if tok['text']['beginOffset'] >= limit:
                g += 1
                limit = self._sentences[g]['text']['beginOffset'] + len(self._sentences[g]['text']['content'])
            if tok['dependencyEdge']['label'] == 'ROOT':
                self._trees[g] = tok
            else:
                self._tokens[ tok['dependencyEdge']['headTokenIndex'] ]['adj'].append(i)
            i += 1

    def getGovenor(self, nodeIdx):
        while self._tokens[nodeIdx]['dependencyEdge']['label'] != 'ROOT':
            if self._tokens[nodeIdx]['partOfSpeech']['tag'] == 'VERB':
                return nodeIdx
            nodeIdx = self._tokens[nodeIdx]['dependencyEdge']['headTokenIndex']
        return None

    def toString(self, idx):
        stk = [ self._tokens[idx] ]
        indexes = [ idx ]
        while len(stk) != 0:
            tok = stk.pop()
            stk.extend(tok['adj'])
            indexes.extend(tok['adj'])
        indexes.sort()
        text = ' '
        for idx in indexes:
            text += self._tokens[idx]['text']['content']
        return text.lstrip()

    def findClauses(self, trees=None):
        iscollection = True
        if trees is None:
            trees = self._trees
        elif not isinstance(trees, collections.Iterable):
            trees = [ trees ]
            iscollection = False

        clauses = [ None ] * len(trees)
        for k in range(len(trees)):
            root = trees[k]
            assert root['dependencyEdge']['label'] == 'ROOT'

            # find all token indexes from this root
            indexes = [ root['dependencyEdge']['headTokenIndex'] ]
            stk = [ root['dependencyEdge']['headTokenIndex'] ]
            while len(stk) != 0:
                i = stk[0]
                stk.pop(0)
                adj = self._tokens[i]['adj']
                stk.extend(adj)
                indexes.extend(adj)

            clauseMap = { }
            for i in indexes:
                label = self._tokens[i]['dependencyEdge']['label']
                if label in [ 'NSUBJ', 'NSUBJPASS', 'CSUBJ', 'CSUBJPASS', 'NOMCSUBJ', 'NOMCSUBJPASS' ]:
                    S = i
                    V = self.getGovenor(i)
                    assert V is not None
                    if clauseMap.has_key(V):
                        clauseMap[V] = [ S ].extend(clauseMap[V])
                    else:
                        clauseMap[V] = [ S, V ]
                elif label in [ 'DOBJ', 'IOBJ', 'CCOMP', 'XCOMP' ]:
                    O = i
                    V = self.getGovenor(i)
                    assert V is not None
                    if clauseMap.has_key(V):
                        clauseMap[V].append(O)
                    else:
                        clauseMap[V] = [ V, O ]

            C = []
            for m in clauseMap:
                clause = { }
                clause['subject'] = {}
                clause['subject']['text'] = self.toString(m[0])
                clause['subject']['index'] = m[0]
                clause['verb'] = {}
                clause['verb']['text'] = self._tokens[m[1]]['text']['content']
                clause['verb']['index'] = m[1]
                if len(m) == 3:
                    clause['type'] = 'SVO'
                    clause['object'] = {}
                    clause['object']['text'] = self.toString(m[2])
                    clause['object']['index'] = m[2]
                else:
                    clause['type'] = 'SV'
                C.append(clause)
            clauses[k] = C

        if not iscollection:
            return clauses[0]
        return clauses

    @property
    def sentences(self):
        return self._sentences

    @property
    def trees(self):
        return self._trees

    @property
    def tokens(self):
        return self._tokens


def getGoogleNlpService():
    '''Build a client to the Google Cloud Natural Language API.'''
    credentials = GoogleCredentials.get_application_default()
    return discovery.build('language', 'v1beta1', credentials=credentials)


def getGoogleNlpRequestBody(text, syntax=True, entities=True, sentiment=False):
    ''' Creates the body of the request to the language api in
    order to get an appropriate api response
    '''
    body = {
        'document': {
            'type': 'PLAIN_TEXT',
            'content': text,
        },
        'features': {
            'extract_syntax': syntax,
            'extract_entities': entities,
            'extract_document_sentiment': sentiment,
        },
        'encoding_type': 'UTF32'
    }
    return body


class GoogleNLP(object):
    '''Google NLP'''

    def __init__(self):
        '''Construct an NLP service'''
        self._service = getGoogleNlpService()

    def parse(self, text):
        '''Parse text and return a DependencyTrees instance

        Args:
            text: The text to parse.

        Returns:
            A DependencyTrees instance.
        '''
        body = getGoogleNlpRequestBody(text)
        request = self._service.documents().annotateText(body=body)
        response = request.execute(num_retries=3)
        return DependencyTrees(response)



