# Google NLP Interface

import dep, pos
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials

class Token(object):
    '''A token in the dependency tree. The class has a similar interface to spacy.Token
    '''

    def __init__(self, doc, offset):
        self._doc = doc
        self._gtok = doc._tokens[offset]
        self._lemma = self._gtok['lemma']
        self._text = self._gtok['text']['content']
        self._dep = dep.TAG[ self._gtok['dependencyEdge']['label'] ]
        self._pos = pos.TAG[ self._gtok['partOfSpeech']['tag'] ]
        self._adj = self._gtok['adj']
        self._idx = offset

    def __repr__(self):
        return '(%i,\"%s\"|%s,%s)' % (self._idx, self._text,self.pos.text,self.dep.text)

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
    def lemme(self):
        return self._lemma

    @property
    def orth(self):
        return self._text

    @property
    def lower(self):
        return self._text.lower()

    @property
    def dep(self):
        return self._dep

    @property
    def pos(self):
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
    def idx(self):
        return self._idx

    @property
    def doc(self):
        return self._doc

    @property
    def text(self):
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

    def isDescendent(self, ancestor):
        token = self
        while token.dep != dep.ROOT:
            if token.idx == ancestor.idx:
                return True
            token = token.head
        return token.idx == ancestor.idx

    def isAncestor(self, descendent):
        return descendent.idx in SubtreeSpan(self._doc, self._idx)._indexes


class Span(object):
    '''View of a document. The class has a similar interface to spacy.Span
    '''

    def __init__(self, doc, indexes=None):
        self._doc = doc
        if indexes is None:
            self._indexes = []
        else:
            self._indexes = indexes

    def __len__(self):
        return len(self._indexes)

    def __getitem__(self, i):
        return Token(self._doc, i)

    def __iter__(self):
        for k in self._indexes:
            yield Token(self._doc, k)

    def __repr__(self):
        return self.text

    def union(self, other):
        '''Union two spans.'''
        if other is None or len(other) == 0: return
        self._indexes.extend(filter(lambda x: x not in self._indexes, other._indexes))
        self._indexes.sort()

    def complement(self, other):
        '''Remove other from this span.'''
        if other is None or len(other) == 0: return
        self._indexes = filter(lambda x: x not in other._indexes, self._indexes)

    def intersect(self, other):
        '''Find common span.'''
        if other is None or len(other) == 0:
            self._indexes = []
            return
        self._indexes = filter(lambda x: x in other._indexes, self._indexes)

    @property
    def text(self):
        if len(self._indexes) == 0:
            return ''
        txt = self._doc._tokens[self._indexes[0]]['text']['content']
        for i in self._indexes[1:]:
            gtok = self._doc._tokens[i]
            if gtok['partOfSpeech']['tag'] == pos.PUNCT.text:
                txt += gtok['text']['content']
            else:
                txt += ' ' + gtok['text']['content']
        return txt

    @property
    def text_with_ws(self):
        return self.text


class SubtreeSpan(Span):
    '''View of a document. Specialization of Span.'''

    def __init__(self, doc, idx=-1, removePunct=False, shallow=False):
        '''Constructor.

        Args:
            idx: A token index or a Token instance.
            removePunct: If True punctuation is excluded from the span.
            shallow: If shallow is a boolean and True then don't add dependent
                tokens to span. If shallow isa list of token indexes these are
                used as the adjacency for the token a idx.
        '''
        if isinstance(doc, Token):
            idx = doc.idx
            doc = doc.doc
            indexes = [idx]
        else:
            indexes = [idx]

        stk = None
        if isinstance(shallow, list):
            if len(shallow) > 0:
                stk = shallow
            shallow = False

        if not shallow:
            if stk is None:
                stk = [x for x in doc[idx]._adj]
            indexes.extend(stk)
            while len(stk) != 0:
                tok = doc[stk.pop()]
                stk.extend(tok._adj)
                indexes.extend(tok._adj)
            '''
            stk = [ idx ]
            while len(stk) != 0:
                gtok = doc._tokens[ stk.pop() ]
                stk.extend(gtok['adj'])
                indexes.extend(gtok['adj'])
            '''
            if removePunct:
                indexes = filter(lambda x: not doc[x].is_punct, indexes)
            indexes.sort()
        super(SubtreeSpan, self).__init__(doc, indexes)
        self._rootIdx = idx

    def __repr__(self):
        if len(self._indexes) == 0:
            return '(%i,\"\")' % self._rootIdx
        txt = '(%i,\"%s' % (self._rootIdx, self._doc._tokens[self._indexes[0]]['text']['content'])
        for i in self._indexes[1:]:
            gtok = self._doc._tokens[i]
            if gtok['partOfSpeech']['tag'] == pos.PUNCT.text:
                txt += gtok['text']['content']
            else:
                txt += ' ' + gtok['text']['content']
        return txt + '\")'

    def repair(self):
        '''If the span no longer includes the root index due to complement or intersect
        operations then this ensures the root idx is included. Also sorts indexes.
        '''
        if self._rootIdx not in self._indexes:
            self._indexes.append(self._rootIdx)
        self._indexes.sort()

    @property
    def root(self):
        '''Return the root of the subtree span.

        Returns: A Token instance.
        '''
        return self._doc[self._rootIdx]

    @property
    def idx(self):
        '''Return the root index of the subtree span.

        Returns: A index onto the Token array.
        '''
        return self._rootIdx


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


