import collections
import os, sys, json, requests
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials
from optparse import OptionParser


POS = {
    'UNKNOWN':'',  # Unknown
    'ADJ':'',      # Adjective
    'ADP':'A',	   # Adposition (preposition and postposition)
    'ADV':'',      # Adverb
    'CONJ':'',     # Conjunction
    'DET':'',      # Determiner
    'NOUN':'',     # Noun (common and proper)
    'NUM':'',	   # Cardinal number
    'PRON':'',     # Pronoun
    'PRT':'',	   # Particle or other function word
    'PUNCT':'',    # Punctuation
    'VERB':'V',    # Verb (all tenses and modes)
    'X':'',        # Other: foreign words:{'type':'', 'model':''}, typos:{'type':'', 'model':''}, abbreviations
    'AFFIX':''     # Affix
}

GRAMMATICAL_RELATIONS = {
    'UNKNOWN':'',      # Unknown
    'ABBREV':'',       # Abbreviation modifier
    'ACOMP':'C',       # Adjectival complement
    'ADVCL':'',        # Adverbial clause modifier
    'ADVMOD':'',	   # Adverbial modifier
    'ADVPHMOD':'',     # Adverbial phrase modifier
    'AMOD':'',         # Adjectival modifier of an NP
    'APPOS':'',        # Appositional modifier of an NP
    'ATTR':'',         # Attribute dependent of a copular verb
    'AUX':'',          # Auxiliary (non-main) verb
    'AUXPASS':'',	   # Passive auxiliary
    'AUXCAUS':'',      # Causative auxiliary
    'AUXVV':'',        # Helper auxiliary
    'CC':'',           # Coordinating conjunction
    'CCOMP':'C',       # Clausal complement of a verb or adjective
    'CONJ':'',         # Conjunct
    'COP':'c',         # Copula
    'CSUBJ':'S',       # Clausal subject
    'CSUBJPASS':'S',   # Clausal passive subject
    'DEP':'',          # Dependency (unable to determine)
    'DET':'',          # Determiner
    'DISCOURSE':'',    # Discourse
    'DISLOCATED':'',   # Dislocated relation (for fronted/topicalized elements)
    'DOBJ':'O',        # Direct object
    'DTMOD':'',        # Rentaishi (Prenominal modifier)
    'EXPL':'',         # Expletive
    'FOREIGN':'',      # Foreign words
    'GOESWITH':'',     # Goes with (part of a word in a text not well edited)
    'IOBJ':'Oi',       # Indirect object
    'KW':'',           # Keyword
    'LIST':'',         # List for chains of comparable items
    'MARK':'',         # Marker (word introducing a subordinate clause)
    'MWE':'',	       # Multi-word expression
    'MWV':'',	       # Multi-word verbal expression
    'NEG':'',          # Negation modifier
    'NN':'',           # Noun compound modifier
    'NOMC':'',         # Nominalized clause
    'NOMCSUBJ':'S',    # Nominalized clausal subject
    'NOMCSUBJPASS':'S',# Nominalized clausal passive
    'NUMC':'',         # Compound of numeric modifier
    'NPADVMOD':'',     # Noun phrase used as an adverbial modifier
    'NSUBJ':'S',       # Nominal subject
    'NSUBJPASS':'S',   # Passive nominal subject
    'NUM':'',          # Numeric modifier of a noun
    'NUMBER':'',       # Element of compound number
    'P':'',            # Punctuation mark
    'PARATAXIS':'',    # Parataxis relation
    'PARTMOD':'',      # Participial modifier
    'PCOMP':'',        # The complement of a preposition is a clause
    'POBJ':'',         # Object of a preposition
    'POSS':'',         # Possession modifier
    'POSTNEG':'',      # Postverbal negative particle
    'PRECOMP':'',      # Predicate complement
    'PRECONJ':'',      # Preconjunt
    'PREDET':'',       # Predeterminer
    'PREF':'',         # Prefix
    'PREP':'',         # Prepositional modifier
    'PRONL':'',        # The relationship between a verb and verbal morpheme
    'PRT':'',          # Particle
    'PS':'',           # Associative or possessive marker
    'QUANTMOD':'',     # Quantifier phrase modifier
    'RCMOD':'',        # Relative clause modifier
    'RCMODREL':'',     # Complementizer in relative clause
    'RDROP':'',        # Ellipsis without a preceding predicate
    'REF':'',          # Referent
    'REMNANT':'',      # Remnant
    'REPARANDUM':'',   # Reparandum
    'ROOT':'',         # Root
    'SNUM':'',         # Suffix specifying a unit of number
    'SUFF':'',         # Suffix
    'SUFFIX':'',       # Name suffix
    'TITLE':'',	       # Name title
    'TMOD':'',         # Temporal modifier
    'TOPIC':'',        # Topic marker
    'VMOD':'',         # Clause headed by an infinite form of the verb that modifies a noun
    'VOCATIVE':'',     # Vocative
    'XCOMP':'C',       # Open clausal complement
}


class Token(object):
    '''A token in the dependency tree. The class has a similar interface to spacy.Token
    '''
    def __init__(self, doc, offset):
        self._doc = doc
        self._gtok = doc._tokens[offset]
        self._lemma = self._gtok['lemma']
        self._text = self._gtok['text']['content']
        self._pos = self._gtok['partOfSpeech']['tag']
        self._idx = offset

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
        return self._gtok['dependencyEdge']['label']

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
        return self._pos == 'PUNCT'

    @property
    def like_num(self):
        return self._pos == 'NUM'

    @property
    def is_space(self):
        return False

    @property
    def idx(self):
        return self._idx

    @property
    def text(self):
        return self._text

    @property
    def head(self):
        return Token(self._doc, self._gtok['dependencyEdge']['headTokenIndex'])

    @property
    def children(self):
        adj = self._gtok['adj']
        for i in adj:
            yield Token(self._doc, i)

    @property
    def subtree(self):
        span = SubtreeSpan(self._doc, self._idx)
        for i in span._indexes:
            yield Token(self._doc, i)

    def isDescendent(self, ancestor):
        token = self
        while token.dep != 'ROOT':
            if token.idx == ancestor.idx:
                return True
            token = token.head
        return token.idx == ancestor.idx

    def isAncestor(self, descendent):
        return descendent.idx in SubtreeSpan(self._doc, self._idx)._indexes


class Span(object):
    '''View of a document. The class has a similar interface to spacy.Span
    '''
    def __init__(self, doc, indexes):
        self._doc = doc
        self._indexes = indexes

    def __len__(self):
        return len(self._indexes)

    def __getitem__(self, i):
        return Token(self._doc, i)

    def __iter__(self):
        for k in self._indexes:
            yield Token(self._doc, k)

    @property
    def text(self):
        if len(self._indexes) == 0:
            return ''
        txt = self._doc._tokens[ self._indexes[0] ]['text']['content']
        for i in self._indexes[1:]:
            gtok = self._doc._tokens[i]
            if gtok['partOfSpeech']['tag'] == 'PUNCT':
                txt += gtok['text']['content']
            else:
                txt += ' ' + gtok['text']['content']
        return txt

    @property
    def text_with_ws(self):
        return self.text


class SubtreeSpan(Span):
    '''View of a document. Specialization of Span.'''
    def __init__(self, doc, idx, removePunct=False):
        stk = [ idx ]
        indexes = [ idx ]
        while len(stk) != 0:
            gtok = doc._tokens[ stk.pop() ]
            stk.extend(gtok['adj'])
            indexes.extend(gtok['adj'])
        if removePunct:
            indexes = filter(lambda x: not doc[x].is_punct, indexes)
        indexes.sort()
        super(SubtreeSpan, self).__init__(doc, indexes)
        self._rootIdx = idx


class Doc(object):
    '''Google NLP Document. The class has a similar interface to spacy.Doc'''

    def __init__(self, nlpResult):
        self._sentences = nlpResult['sentences']
        self._tokens = nlpResult['tokens']
        self._trees = [ None ] * len(self._sentences)
        g = -1
        for tok in self._tokens:
            tok['adj'] = []
        i = 0
        limit = -1
        for tok in self._tokens:
            if tok['text']['beginOffset'] >= limit:
                g += 1
                limit = self._sentences[g]['text']['beginOffset'] + len(self._sentences[g]['text']['content'])
            if tok['dependencyEdge']['label'] == 'ROOT':
                self._trees[g] = tok
            else:
                self._tokens[ tok['dependencyEdge']['headTokenIndex'] ]['adj'].append(i)
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
        span = SubtreeSpan(self, range(len(self._tokens)))
        return span.text

    @property
    def text_with_ws(self):
        span = SubtreeSpan(self, range(len(self._tokens)))
        return span.text_with_ws

    @property
    def sents(self):
        for t in self._trees:
            yield SubtreeSpan(self, t['dependencyEdge']['headTokenIndex'])


class Clause(object):
    '''Clause in a sentence.'''

    def __init__(self, doc, type, subject, verb, objects=None, module=None):
        if not isinstance(doc, Doc):
            raise TypeError
        self._doc = doc
        self._type = type
        if not isinstance(subject, Token):
            raise TypeError
        self._subj = subject
        if not isinstance(verb, Token):
            raise TypeError
        self._verb = verb

        # Calculate span of objects
        self._subjSpan = SubtreeSpan(doc, subject.idx, removePunct=True)
        if objects is not None:
            if isinstance(objects, collections.Iterable):
                self._objs = objects
                self._objSpans = []
                for o in objects:
                    if not isinstance(o, Token):
                        raise TypeError
                    self._objSpans.append(SubtreeSpan(doc, o.idx, removePunct=True))
                # O(n^2) but len(objects) is typically < 3
                for o,s in zip(objects,self._objSpans):
                    for p,t in zip(objects,self._objSpans):
                        if p.idx == o.idx:
                            continue
                        if p.isDescendent(o):
                            o._indexes = filter(lambda x: x not in p._indexes, o._indexes)
                        elif o.isDescendent(p):
                            p._indexes = filter(lambda x: x not in o._indexes, p._indexes)
            else:
                if not isinstance(objects, Token):
                    raise TypeError
                self._objs = [ objects ]
                self._objSpans = [ SubtreeSpan(doc, objects.idx) ]
        else:
            self._objs = None
            self._objSpans = Span(doc, [])
        # Calculate span of verb - remove objects and subject spans
        # remove indexes from our span
        toRem = []
        toRem.extend(self._subjSpan._indexes)
        for s in self._objSpans:
            toRem.extend(s._indexes)
        complement = filter(lambda x: x not in toRem, SubtreeSpan(doc, verb.idx, removePunct=True)._indexes)
        self._span = Span(doc, complement)

    @property
    def text(self):
        txt = '(%s) (%s)' % (self._subjSpan.text, self._span.text)
        for s in self._objSpans:
            txt += ' (%s)' % s.text
        return txt

    @property
    def type(self):
        return self._type

    @property
    def subject(self):
        return (self._subj, self._subjSpan)

    @property
    def root(self):
        return (self._verb, self._span)

    def numObjects(self):
        return len(self._objsSpan)

    def object(self, i):
        return (self._objs[i], self._objSpans[i])


class ClauseFinder(object):
    '''Find the clauses in a document span'''
    def __init__(self, sentence):
        if not isinstance(sentence, SubtreeSpan):
            raise TypeError
        self._span = sentence
        self._doc = sentence._doc

    def getGovenor(self, token):
        while token.dep != 'ROOT':
            if token.pos == 'VERB':
                return token
            token = token.head
        return token

    def findClauses(self):
        clauseMap =  [ None ] * len(self._doc._tokens)
        # find all token indexes from this root
        i = 0
        for token in self._span:
            if token.dep in [ 'NSUBJ', 'NSUBJPASS', 'CSUBJ', 'CSUBJPASS', 'NOMCSUBJ', 'NOMCSUBJPASS' ]:
                S = token
                V = self.getGovenor(token)
                if clauseMap[V.idx] is not None:
                    if clauseMap[V.idx][1].idx != V.idx:
                        clauseMap[V.idx] = [ S ].extend(clauseMap[V.idx])
                else:
                    clauseMap[V.idx] = [ S, V ]
            elif token.dep in [ 'DOBJ', 'IOBJ', 'CCOMP', 'XCOMP', 'ACOMP' ] or token.pos in [ 'ADP' ]:
                O = token
                V = self.getGovenor(token)
                if clauseMap[V.idx] is not None:
                    clauseMap[V.idx].append(O)
                else:
                    clauseMap[V.idx] = [ V, O ]
            i += 1

        clauses = []
        for m in clauseMap:
            if m is None: continue
            type = ''
            for tok in m:
                type += POS[tok.pos] + GRAMMATICAL_RELATIONS[tok.dep]
            if len(m) >= 3:
                clauses.append(Clause(doc=self._doc, type=type, subject=m[0], verb=m[1], objects=m[2:]))
            else:
                clauses.append(Clause(doc=self._doc, type=type, subject=m[0], verb=m[1]))
        return clauses


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
        return request.execute(num_retries=3)


def die(msg):
    print('Error: %s' % msg)
    sys.exit(1)


if __name__ == '__main__':
    print('Google NLP Interface')

    # Parse command line
    usage = '%prog [options] [text]'
    parser = OptionParser(usage)
    parser.add_option('-j', '--json-in', type='string', dest='jsoninfile', help='Process a Google NLP response.')
    parser.add_option('-o', '--json-out', type='string', dest='jsonoutfile', help='Save Google NLP response.')
    parser.add_option('-f', '--file', type='string', dest='infile', help='Process a text file.')
    parser.add_option('-a', '--appos', action='store_true', dest='compact', help='handle appositional modifiers.')
    parser.add_option('-c', '--compact', action='store_true', dest='compact', help='compact json output.')
    options, args = parser.parse_args()

    if options.jsoninfile is not None:
        print('Processing json file %s' % options.jsoninfile)
        with open(options.jsoninfile, 'rt') as fd:
            doc = Doc(json.load(fd))
            for s in doc.sents:
                cf = ClauseFinder(s)
                clauses = cf.findClauses()
                for clause in clauses:
                    print('%s: %s' % (clause.type, clause.text))

    if options.infile is not None:
        print('Processing text file %s' % options.infile)
        nlp = GoogleNLP()
        with open(options.infile, 'rt') as fd:
            lines = fd.readlines()
        cleanlines = []
        for ln in lines:
            ln = ln.strip()
            if len(ln) == 0 or ln[0] == '#':
                continue
            cleanlines.append(ln)
        result = nlp.parse(' '.join(cleanlines))
        if options.jsonoutfile is not None:
            with open(options.jsonoutfile, 'w') as fd:
                if options.compact:
                    json.dump(result, fp=fd)
                else:
                    json.dump(result, fp=fd, indent=2)
        doc = Doc(result)
        for s in doc.sents:
            cf = ClauseFinder(s)
            clauses = cf.findClauses()
            for clause in clauses:
                print('%s: %s' % (clause.type, clause.text))
    elif len(args) != 0:
        nlp = GoogleNLP()

    if args is not None and len(args) != 0:
        print('Processing command line text')
        nlp.parse(''.join(args))
        doc = Doc(result)
        for s in doc.sents:
            cf = ClauseFinder(s)
            clauses = cf.findClauses()
            for clause in clauses:
                print('%s: %s' % (clause.type, clause.text))


