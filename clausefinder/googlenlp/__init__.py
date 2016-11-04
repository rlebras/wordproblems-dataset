# Google NLP Interface

from . import dep
from . import pos
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials
from clausefinder.common import IndexSpan as Span
from clausefinder.common import SubtreeSpan

GOOGLE_TYPE_NAMES = {
    dep.ACOMP.id: 'C',        # Adjectival complement
    dep.ADVMOD.id: 'Av',      # Adverbial modifier
    dep.ATTR.id: 'c',         # Attribute dependent of a copular verb
    dep.CCOMP.id: 'Cz',       # Clausal complement of a verb or adjective
    dep.CSUBJ.id: 'S',        # Clausal subject
    dep.CSUBJPASS.id: 'S',    # Clausal passive subject
    dep.DOBJ.id: 'O',         # Direct object
    dep.IOBJ.id: 'Oi',        # Indirect object
    dep.NOMCSUBJ.id: 'S',     # Nominalized clausal subject
    dep.NOMCSUBJPASS.id: 'S', # Nominalized clausal passive
    dep.NSUBJ.id: 'S',        # Nominal subject
    dep.NSUBJPASS.id: 'S',    # Passive nominal subject
    dep.QUANTMOD.id: 'Aq',    # Quantifier phrase modifier
    dep.XCOMP.id: 'Cx',       # Open clausal complement
    pos.ADP.id: 'A',          # Adposition (preposition and postposition)
    pos.VERB.id: 'V',         # Verb (all tenses and modes)
}


def getTypeName(tag):
    '''Get a google type string from the grammatical relation id.

    Args:
        tag: The grammatical-relation or part-of-speech tag.

    Returns:
        A string.
    '''
    if GOOGLE_TYPE_NAMES.has_key(tag.id):
        return GOOGLE_TYPE_NAMES[tag.id]
    return ''


class Token(object):
    '''A token in the dependency tree. The class has a similar interface to spacy.Token
    '''

    def __init__(self, doc, offset):
        self._doc = doc
        self._gtok = doc._tokens[offset]
        self._lemma = None  # self._gtok['lemma']
        self._text = None   # self._gtok['text']['content']
        self._dep = None    # dep.TAG[ self._gtok['dependencyEdge']['label'] ]
        self._pos = None    # pos.TAG[ self._gtok['partOfSpeech']['tag'] ]
        self._adj = self._gtok['adj']
        self._idx = offset

    def __repr__(self):
        return '(%i,\"%s\"|%s,%s)' % (self._idx, self.text, self.pos.text, self.dep.text)

    def __eq__(self, other):
        return isinstance(other, Token) and other._idx == self._idx and other._doc._hash == self._doc._hash

    def __ne__(self, other):
        return not isinstance(other, Token) or other._idx != self._idx or other._doc._hash != self._doc._hash

    def __lt__(self, other):
        return other._idx < self._idx

    def __gt__(self, other):
        return other._idx > self._idx

    def __le__(self, other):
        return other._idx <= self._idx

    def __ge__(self, other):
        return other._idx >= self._idx

    def __hash__(self):
        return (self._idx << 5) ^ (self.idx >> 27) ^ self._doc._hash

    @property
    def lemma(self):
        if self._lemma is None:
            self._lemma = self._gtok['lemma']
        return self._lemma

    @property
    def orth(self):
        return self.text

    @property
    def lower(self):
        return self.text.lower()

    @property
    def dep(self):
        if self._dep is None:
            self._dep = dep.TAG[self._gtok['dependencyEdge']['label']]
        return self._dep

    @property
    def pos(self):
        if self._pos is None:
            self._pos = pos.TAG[self._gtok['partOfSpeech']['tag']]
        return self._pos

    @property
    def shape(self):
        raise NotImplementedError

    @property
    def prefix(self):
        raise NotImplementedError

    @property
    def suffix(self):
        raise NotImplementedError

    @property
    def is_punct(self):
        return self._pos == pos.PUNCT

    @property
    def like_num(self):
        return self._pos == pos.NUM

    @property
    def is_space(self):
        return False

    @property
    def i(self):
        return self._idx

    @property
    def doc(self):
        return self._doc

    @property
    def text(self):
        if self._text is None:
            self._text = self._gtok['text']['content']
        return self._text

    @property
    def head(self):
        return Token(self._doc, self._gtok['dependencyEdge']['headTokenIndex'])

    @property
    def children(self):
        for i in self._adj:
            yield Token(self._doc, i)

    @property
    def subtree(self):
        span = SubtreeSpan(self._doc, self._idx)
        for i in span._indexes:
            yield Token(self._doc, i)



class Doc(object):
    '''Google NLP Document. The class has a similar interface to spacy.Doc'''

    def __init__(self, nlpResult):
        '''Construct a document form a Google NLP result.

        Args:
            nlpResult: The result of a GoogleNLP.parse() call.
        '''
        self._sentences = nlpResult['sentences']
        self._tokens = nlpResult['tokens']
        self._trees = [None] * len(self._sentences)
        self._hash = 0
        g = -1
        for tok in self._tokens:
            tok['adj'] = []
            self._hash ^= hash(tok['text']['content'])
        i = 0
        limit = -1
        for tok in self._tokens:
            if tok['text']['beginOffset'] >= limit:
                g += 1
                limit = self._sentences[g]['text']['beginOffset'] + len(self._sentences[g]['text']['content'])
            if tok['dependencyEdge']['label'] == dep.ROOT.text:
                self._trees[g] = tok
            else:
                self._tokens[tok['dependencyEdge']['headTokenIndex']]['adj'].append(i)
            i += 1

    def __getitem__(self, slice_i_j):
        if isinstance(slice_i_j, slice):
            return Span(self, range(slice_i_j))
        return Token(self, slice_i_j)

    def __iter__(self):
        for i in range(len(self._tokens)):
            yield Token(self, i)

    def __len__(self):
        return len(self._tokens)

    @property
    def text(self):
        span = Span(self, range(len(self._tokens)))
        return span.text

    @property
    def text_with_ws(self):
        span = Span(self, range(len(self._tokens)))
        return span.text_with_ws

    @property
    def sents(self):
        for t in self._trees:
            yield SubtreeSpan(self, t['dependencyEdge']['headTokenIndex'])


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
        '''Parse text and return result as per Google NLP API spec. The
        result can be used to construct a Doc instance.

        Args:
            text: The text to parse.

        Returns:
            A Google NLP result.
        '''
        body = getGoogleNlpRequestBody(text)
        request = self._service.documents().annotateText(body=body)
        return request.execute(num_retries=3)


