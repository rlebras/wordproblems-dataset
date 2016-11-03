import collections
import os, sys, json
from optparse import OptionParser
import states
import googlenlp
import spacynlp
from clausefinder.common import ClauseFinderMap
from clausefinder.common import SyntheticSpan
from clausefinder.common import IndexSpan
from clausefinder.common import SubtreeSpan


class Clause(object):
    '''View of a clause in a sentence.'''

    def __init__(self, doc, type, subjectSpan, verbSpan, objectSpans):
        if isinstance(doc, googlenlp.Doc):
            self._nlp = googlenlp
        elif isinstance(doc, spacynlp.Doc):
            self._nlp = spacynlp
        else:
            raise TypeError
        self._doc = doc
        self._type = type
        self._subjSpan = subjectSpan
        self._span = verbSpan
        if isinstance(objectSpans, SubtreeSpan):
            self._objSpans = [ objectSpans ]
        else:
            self._objSpans = objectSpans

        # Now do final fixup
        self._subjSpan._indexes = filter(lambda x: x <= subjectSpan.idx, subjectSpan._indexes)
        # Handle synthetic spans
        if isinstance(verbSpan, IndexSpan):
            self._span._indexes = filter(lambda x: x <= verbSpan.idx, verbSpan._indexes)
        '''
        for s in self._objSpans:
            # Truncate after first occurrence of punctuation or conjunction
            i = -1
            first = 0
            last = -1
            for o in s:
                i = i + 1
                if o.idx < s.idx:
                    if o.is_punct or o.pos == googlenlp.pos.CONJ:
                        first = i + 1
                elif o.idx > s.idx:
                    if o.is_punct or o.pos == googlenlp.pos.CONJ:
                        last = i
                        break
            if first > 0 or last > 0:
                s._indexes = s._indexes[first:last]
        '''

    def __repr__(self):
        return '<' + self.text + '>'

    @property
    def text(self):
        '''Return a string represent the compoents of the clause.'''
        txt = '(%s) (%s)' % (self._subjSpan.text, self._span.text)
        for s in self._objSpans:
            txt += ' (%s)' % s.text
        return txt

    @property
    def type(self):
        '''Return the type of clause.'''
        return self._type

    @property
    def subject(self):
        '''Return the subject span. Use subject.root to get the token.'''
        return self._subjSpan

    @property
    def root(self):
        '''Return verb span. Use root.root to get the token.'''
        return self._span

    def numObjects(self):
        '''Return the number of object tokens.'''
        return len(self._objsSpan)

    def object(self, i):
        '''Return object span at index i.  Use object(i).root to get the token.'''
        return self._objSpans[i]


class ParsedClause(Clause):
    '''View of a clause in a sentence.'''

    def __init__(self, doc, type, subject, verb, objects=None, exclude=None, merge=None):
        module = None
        if isinstance(doc, googlenlp.Doc):
            module = googlenlp
        elif isinstance(doc, spacynlp.Doc):
            module = spacynlp
        else:
            raise TypeError

        if not isinstance(subject, module.Token):
            raise TypeError
        if not isinstance(verb, module.Token):
            raise TypeError

        # Calculate excluded token span
        excludeSpan = IndexSpan(doc)
        if exclude is not None:
            for x in exclude:
                if isinstance(x, module.Token):
                    excludeSpan.union(SubtreeSpan(x))
                elif isinstance(x, list):
                    if len(x) > 0:
                        if isinstance(x[0], module.Token):
                            excludeSpan._indexes.extend(
                                filter(lambda y: y not in excludeSpan._indexes, [y.idx for y in x]))
                        else:
                            raise TypeError
                else:
                    raise TypeError

        # Calculate span of subject
        subjSpan = SubtreeSpan(subject)
        subjSpan.complement(excludeSpan)
        if len(subjSpan) == 0:
            subjSpan._indexes = [subject.idx]

        # Calculate span of objects
        if objects is not None:
            if isinstance(objects, collections.Iterable):
                objSpans = []
                for o in objects:
                    if not isinstance(o, (googlenlp.Token, spacynlp.Token)):
                        raise TypeError
                    objSpans.append(SubtreeSpan(o))
                # O(n^2) but len(objects) is typically < 3
                for o, s in zip(objects, objSpans):
                    for p, t in zip(objects, objSpans):
                        if p.idx == o.idx:
                            continue
                        if p.isDescendent(o):
                            s._indexes = filter(lambda x: x not in t._indexes, s._indexes)
                        elif o.isDescendent(p):
                            t._indexes = filter(lambda x: x not in s._indexes, t._indexes)
            else:
                if not isinstance(objects, (googlenlp.Token, spacynlp.Token)):
                    raise TypeError
                objSpans = [SubtreeSpan(objects)]
        else:
            objSpans = []

        # Calculate span of verb - remove objects, subject, and exclude spans
        # Calc indexes to remove from verb span
        toRem = []
        toRem.extend(subjSpan._indexes)
        toRem.extend(excludeSpan._indexes)
        emptyObjs = []
        for i in reversed(range(len(objSpans))):
            s = objSpans[i]
            # Remove exclude region form object spans
            s.complement(excludeSpan)
            toRem.extend(s._indexes)
            # Remove dep mark starting a span
            if len(s._indexes) > 0 and doc[s._indexes[0]].dep == module.dep.MARK:
                s._indexes.pop(0)
            s.repair()

        verbSpan = SubtreeSpan(verb, shallow=True)
        if verb.idx > 0 and doc[verb.idx].dep == module.dep.AUXPASS:
            verbSpan._indexes = [verb.idx-1, verb.idx]
        '''
        complement = filter(lambda x: x not in toRem, verbSpan._indexes)
        if len(complement) == 0:
            complement = [verb.idx]
        verbSpan._indexes = complement
        '''
        subjSpan.repair()
        verbSpan.repair()
        # Process merges formatted as: [ [focusIdx1, idx1, ...], [focusIdx2, idxN, ...]]
        if merge is not None and len(merge) > 0:
            for m in merge:
                focus = objSpans[ m[0] ]
                m = m[1:]
                m.sort()
                for i in reversed(m):
                    focus.union(objSpans[i])
                    objSpans.pop(i)
        # Finally call base class
        super(ParsedClause, self).__init__(doc=doc, type=type, subjectSpan=subjSpan, verbSpan=verbSpan, objectSpans=objSpans)


class ClauseFinder(object):
    '''Class to find the clauses in a document.'''

    def __init__(self, doc):
        '''Constructor.

        Args:
             doc: A google.Doc or spacy.Doc
        '''
        if isinstance(doc, googlenlp.Doc):
            self._nlp = googlenlp
        elif isinstance(doc, spacynlp.Doc):
            self._nlp = spacynlp
        else:
            raise TypeError
        self._doc = doc
        self._map = ClauseFinderMap(doc)
        self._conjAMap = ClauseFinderMap(doc)
        self._conjOMap = ClauseFinderMap(doc)
        self._conjVMap = ClauseFinderMap(doc)

    def _processAsObj(self, O, V=None):
        if V is None: V = self.getGovenorVerb(O)
        if V is None: return
        if not self._map.insertNew(V, [V, O]):
            self._map.append(V, O)

    def _processAsSubj(self, S, V=None):
        if V is None: V = self.getGovenorVerb(S)
        if V is None:
            return
        elif not self._map.insertNew(V, [S, V]):
            X = self._map.lookup(V)
            if X[1].idx != V.idx:
                newX = [S]
                newX.extend(X)
                self._map.replace(V, newX)

    def _processConj(self, token):
        A = self.getFirstOfConj(token)
        V = self.getGovenorVerb(A)
        if V is not None:
            if A.pos == self._nlp.pos.VERB:
                assert token.pos == self._nlp.pos.VERB
                assert A == V
                assert V != token
                self._conjVMap.insertNew(V, [A])
                self._conjVMap.append(V, token)
            elif A.dep in [self._nlp.dep.DOBJ, self._nlp.dep.IOBJ, self._nlp.dep.ACOMP]:
                self._conjOMap.insertNew(V, [A])
                self._conjOMap.append(V, token)
            else:
                O = self.getGovenorObj(A)
                if O is not None:
                    self._conjAMap.insertNew(O, [A])
                    self._conjAMap.append(O, token)

    def _checkIfConj(self, token):
        O = token.head
        V = self.getGovenorVerb(O)
        if V is not None:
            if O.pos == self._nlp.pos.VERB or \
                            O.dep in [self._nlp.dep.DOBJ, self._nlp.dep.IOBJ, self._nlp.dep.ACOMP] or \
                            self.getGovenorObj(O) is not None:
                return True
        return False

    def getGovenorVerb(self, token):
        '''Get the verb govenor of token. If the verb is part of a conjunction
         then the head of conjunction is returned.

        Args:
            token: A Token instance.

        Returns:
            The govenor verb if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if token.pos == self._nlp.pos.VERB:
                # Trace conjunctions
                while token.dep == self._nlp.dep.CONJ and token.head.pos == self._nlp.pos.VERB:
                    token = token.head
                return token
            token = token.head
        if token.pos == self._nlp.pos.VERB:
            return token
        return None

    def getGovenorPOS(self, token, pos):
        '''Get the govenor part-of-speech of token.

        Args:
            token: A Token instance.
            pos: The part-of-speech

        Returns:
            The govenor part-of-speech if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if token.pos in pos:
                return token
            token = token.head
        if token.pos in pos:
            return token
        return None

    def getGovenorNsubj(self, token):
        '''Get the govenor subject token.

        Args:
            token: A Token instance.

        Returns:
            The govenor subject if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if token.dep == self._nlp.dep.NSUBJ:
                return token
            token = token.head
        return None

    def getGovenorObj(self, token):
        '''Get the govenor object token.

        Args:
            token: A Token instance.

        Returns:
            The govenor object if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if token.dep in [self._nlp.dep.DOBJ, self._nlp.dep.IOBJ, self._nlp.dep.ACOMP]:
                return token
            token = token.head
        return None

    def getFirstOfConj(self, token):
        '''Get the first conjunction linking to token.

        Args:
            token: A Token instance.

        Returns:
            The first token in the conjunction.
        '''
        assert token.dep == self._nlp.dep.CONJ
        while token.dep != self._nlp.dep.ROOT:
            if token.dep != self._nlp.dep.CONJ:
                return token
            token = token.head
        return token

    def findClauses(self, sentence):
        '''Find all clauses in a sentence.

        Args:
            sentence: A Span describing a sentence.

        Returns:
            A list of Clause instances or a Clause instance.
        '''
        if not isinstance(sentence, (SubtreeSpan, spacynlp.Span)):
            raise TypeError
        # Reset lookup tables
        self._map.clear()
        self._conjAMap.clear()
        self._conjOMap.clear()
        self._conjVMap.clear()
        excludeList = []
        coordList = []
        clauses = []
        state = (states.ROOT_FIND, None)
        stk = [ ]
        # find all token indexes from this root
        for token in sentence:
            if state[0] == states.NSUBJ_FIND:
                if self.getGovenorNsubj(token) != state[1]:
                    state = stk.pop(-1)
                #else:
                #    excludeList.append(token)

            # 'NSUBJPASS', 'CSUBJ', 'CSUBJPASS', 'NOMCSUBJ', 'NOMCSUBJPASS'
            if token.dep  == self._nlp.dep.NSUBJ:
                self._processAsSubj(token)

            elif token.dep == self._nlp.dep.NSUBJPASS:
                if token.text.lower() in ['which', 'that']:
                    S = self.getGovenorNsubj(token)
                    if S is None:
                        self._processAsSubj(token)
                    else:
                        V = self.getGovenorVerb(token)
                        if V is not None:
                            stk.append(state)
                            excludeList.append(token)
                            state = (states.NSUBJ_FIND, S)
                            self._processAsSubj(S, V)
                        else:
                            self._processAsSubj(token)
                else:
                    self._processAsSubj(token)

            # 'XCOMP','CCOMP','ATTR'
            elif token.pos == self._nlp.pos.ADP:
                if token.head.dep in [self._nlp.dep.ADVMOD, self._nlp.dep.QUANTMOD] and (token.head.idx + 1) == token.idx:
                    self._processAsObj(token.head, self.getGovenorVerb(token))
                else:
                    self._processAsObj(token, self.getGovenorVerb(token))

            elif token.dep in [self._nlp.dep.DOBJ, self._nlp.dep.IOBJ, self._nlp.dep.ACOMP, self._nlp.dep.ATTR]:
                self._processAsObj(token)

            elif token.dep == self._nlp.dep.APPOS:
                # Check if we need to create a synthetic is-a relationship
                if token.head.dep in [self._nlp.dep.NSUBJ, self._nlp.dep.NSUBJPASS]:
                    if state[0] == states.NSUBJ_FIND:
                        assert token.head.dep == self._nlp.dep.NSUBJPASS
                        S = state[1]
                    else:
                        S = token.head
                    excludeList.append(token)
                    clauses.append(Clause(self._doc, \
                                          type='ISA', \
                                          subjectSpan=self._nlp.SubtreeSpan(S, shallow=True), \
                                          verbSpan=SyntheticSpan('is'), \
                                          objectSpans=self._nlp.SubtreeSpan(token)))
                    S = None
            elif token.dep == self._nlp.dep.CONJ:
                # Find the first conjunction and label all other the same
                self._processConj(token)

            elif token.dep == self._nlp.dep.CC:
                # Save for later. This will be excluded when we expand conjunctions
                if self._checkIfConj(token):
                    coordList.append(token)

            elif token.dep in [self._nlp.dep.XCOMP, self._nlp.dep.CCOMP]:
                # Xcomp can have a VERB or ADJ as a parent
                VA = self.getGovenorPOS(token.head, [self._nlp.pos.VERB, self._nlp.pos.ADJ])
                if VA is not None:
                    if VA.dep == self._nlp.dep.ROOT:
                        # OK token will be used as is
                        V = VA
                        VA = token
                    else:
                        # TODO: can we further decompose xcomp
                        V = self.getGovenorVerb(VA.head)
                        if V is None: continue
                    if not self._map.insertNew(V, [V, VA]):
                        if VA not in self._map.lookup(V):
                            self._map.append(V, VA)

        for k, m in self._map:
            if m is None or self._nlp.getTypeName(m[0].dep) != 'S': continue
            type = ''
            for tok in m:
                type += self._nlp.getTypeName(tok.pos) + self._nlp.getTypeName(tok.dep)

            if len(m) >= 3:
                # Check for conjunctions. Iterate and replace the object in SVO.
                conjVList = self._conjVMap.lookup(m[1])
                if conjVList is None:
                    conjVList = [m[1]]
                else: # sanity check
                    assert m[1] == conjVList[0]
                conjOList = self._conjOMap.lookup(m[1])
                if conjOList is None:
                    conjOList = [m[2]]
                else:
                    assert m[2] == conjOList[0]

                if len(m) > 3:
                    objs = [ None, None ]
                    objs.extend(m[3:])
                else:
                    objs = [ None, None ]

                exclude = excludeList
                exclude.extend(coordList)
                for V in conjVList:
                    for O in conjOList:
                        objs[1] = O
                        conjAList = self._conjAMap.lookup(m[2])
                        if conjAList is None:
                            clauses.append(ParsedClause(doc=self._doc, type=type, subject=m[0], verb=V, objects=objs[1:],
                                                        exclude=exclude))
                        else:
                            excludeA = exclude
                            if conjAList[0].dep == self._nlp.dep.AMOD:
                                # Tell ParsedClause to combine objs[0:2] into a single term
                                merge = [ [1,0] ]
                            else:
                                merge = None
                            for i in range(len(conjAList)):
                                A = conjAList[i]
                                objs[0] = A
                                x = []
                                x.extend(excludeA)
                                x.extend(conjAList[i+1:])
                                clauses.append(ParsedClause(doc=self._doc, type=type, subject=m[0], verb=V, objects=objs,
                                                            exclude=x, merge=merge))
                                excludeA.append(A)
                            objs[0] = None
                        objs[1] = None
            else:
                conjVList = self._conjVMap.lookup(m[1])
                if conjVList is None:
                    conjVList = [m[1]]
                else: # sanity check
                    assert m[1] == conjVList[0]
                for V in conjVList:
                    clauses.append(ParsedClause(doc=self._doc, type=type, subject=m[0], verb=V, exclude=excludeList))

        return clauses


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
    parser.add_option('-p', '--parser', type='string', dest='parser', help='Parsers to invoke (google|spacy), default is google.')
    options, args = parser.parse_args()

    parser = options.parser or 'google'
    if parser not in ['google', 'spacy']:
        die('bad --parser=%s option' % parser)
    if parser != 'google' and options.jsoninfile is not None:
        print('Warning --json-in only available for google parser')
    if parser != 'google' and options.jsonoutfile is not None:
        print('Warning --json-out only available for google parser')

    if parser == 'google':
        i = 1
        if options.jsoninfile is not None:
            # Always google in this case
            print('Processing json file %s' % options.jsoninfile)
            with open(options.jsoninfile, 'rt') as fd:
                doc = googlenlp.Doc(json.load(fd))
                i = 1
                cf = ClauseFinder(doc)
                for s in doc.sents:
                    clauses = cf.findClauses(s)
                    for clause in clauses:
                        print('%i. %s: %s' % (i, clause.type, clause.text))
                    i += 1

        if options.infile is not None:
            print('Processing text file %s' % options.infile)
            nlp = googlenlp.GoogleNLP()
            with open(options.infile, 'rt') as fd:
                lines = fd.readlines()
            cleanlines = filter(lambda x: len(x) != 0 and x[0] != '#', [x.strip() for x in lines])
            result = nlp.parse(' '.join(cleanlines))
            if options.jsonoutfile is not None:
                with open(options.jsonoutfile, 'w') as fd:
                    if options.compact:
                        json.dump(result, fp=fd)
                    else:
                        json.dump(result, fp=fd, indent=2)
            doc = googlenlp.Doc(result)
            cf = ClauseFinder(doc)
            for s in doc.sents:
                clauses = cf.findClauses(s)
                for clause in clauses:
                    print('%i. %s: %s' % (i, clause.type, clause.text))
                i += 1

        elif len(args) != 0:
            nlp = googlenlp.GoogleNLP()

        if args is not None and len(args) != 0:
            print('Processing command line text')
            nlp.parse(''.join(args))
            doc = googlenlp.Doc(result)
            cf = ClauseFinder(doc)
            for s in doc.sents:
                clauses = cf.findClauses(s)
                for clause in clauses:
                    print('%s: %s' % (clause.type, clause.text))
    else:
        i = 1
        if options.infile is not None:
            print('Processing text file %s' % options.infile)
            with open(options.infile, 'rt') as fd:
                lines = fd.readlines()
            cleanlines = filter(lambda x: len(x) != 0 and x[0] != '#', [x.strip() for x in lines])
            doclist = spacynlp.parse(' '.join(cleanlines).decode('utf-8'))
            for doc in doclist:
                cf = ClauseFinder(doc)
                for s in doc.sents:
                    clauses = cf.findClauses(s)
                    for clause in clauses:
                        print('%i. %s: %s' % (i, clause.type, clause.text))
                    i += 1


    sys.exit(0)