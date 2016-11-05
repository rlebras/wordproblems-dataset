import collections
import states
import googlenlp
import spacynlp
from clausefinder.common import ClauseFinderMap
from clausefinder.common import SyntheticSpan
from clausefinder.common import IndexSpan
from clausefinder.common import SubtreeSpan


#def isAncestor(token, descendent):
#    return descendent.i in SubtreeSpan(self._doc, self._idx)._indexes

def is_descendant(token, ancestor, module):
    '''Check if token is a descendant of ancestor.

    Args:
        token: The token to test.
        ancestor: The potential ancestor of token.
        module: googlenlp or spacynlp

    Returns:
        True if token is a descendant of ancestor.
    '''
    while token.dep != module.dep.ROOT:
        if token.i == ancestor.i:
            return True
        token = token.head
    return token.i == ancestor.i


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
        self._subjSpan._indexes = filter(lambda x: x <= subjectSpan.i, subjectSpan._indexes)
        # Handle synthetic spans
        if isinstance(verbSpan, IndexSpan):
            self._span._indexes = filter(lambda x: x <= verbSpan.i, verbSpan._indexes)
        '''
        for s in self._objSpans:
            # Truncate after first occurrence of punctuation or conjunction
            i = -1
            first = 0
            last = -1
            for o in s:
                i = i + 1
                if o.i < s.i:
                    if o.is_punct or o.pos == googlenlp.pos.CONJ:
                        first = i + 1
                elif o.i > s.i:
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

    @property
    def objects(self):
        '''Iterate objects.

        Yields:
            A SubjectSpan instance.
        '''
        for o in self._objSpans:
            yield o


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
                                filter(lambda y: y not in excludeSpan._indexes, [y.i for y in x]))
                        else:
                            raise TypeError
                else:
                    raise TypeError

        # Calculate span of subject
        subjSpan = SubtreeSpan(subject)
        subjSpan.complement(excludeSpan)
        if len(subjSpan) == 0:
            subjSpan._indexes = [subject.i]

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
                        if p.i == o.i:
                            continue
                        if is_descendant(p, o, module):
                            s._indexes = filter(lambda x: x not in t._indexes, s._indexes)
                        elif is_descendant(o, p, module):
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
        if verb.i > 0 and doc[verb.i].dep == module.dep.AUXPASS:
            verbSpan._indexes = [verb.i-1, verb.i]
        '''
        complement = filter(lambda x: x not in toRem, verbSpan._indexes)
        if len(complement) == 0:
            complement = [verb.i]
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

    def _process_as_obj(self, O, V=None):
        if V is None: V = self.get_governor_verb(O)
        if V is None: return
        if not self._map.insert_new(V, [V, O]):
            self._map.append(V, O)

    def _process_as_subj(self, S, V=None):
        if V is None: V = self.get_governor_verb(S)
        if V is None:
            return
        elif not self._map.insert_new(V, [S, V]):
            X = self._map.lookup(V)
            if X[1].i != V.i:
                newX = [S]
                newX.extend(X)
                self._map.replace(V, newX)

    def _process_conj(self, token):
        A = self.get_first_of_conj(token)
        V = self.get_governor_verb(A)
        if V is not None:
            if A.pos == self._nlp.pos.VERB:
                assert token.pos == self._nlp.pos.VERB
                assert A == V
                assert V != token
                self._conjVMap.insert_new(V, [A])
                self._conjVMap.append(V, token)
            elif A.dep in [self._nlp.dep.DOBJ, self._nlp.dep.IOBJ, self._nlp.dep.ACOMP]:
                self._conjOMap.insert_new(V, [A])
                self._conjOMap.append(V, token)
            else:
                O = self.get_governor_obj(A)
                if O is not None:
                    self._conjAMap.insert_new(O, [A])
                    self._conjAMap.append(O, token)

    def _check_conj(self, token):
        O = token.head
        V = self.get_governor_verb(O)
        if V is not None:
            if O.pos == self._nlp.pos.VERB or \
                            O.dep in [self._nlp.dep.DOBJ, self._nlp.dep.IOBJ, self._nlp.dep.ACOMP] or \
                            self.get_governor_obj(O) is not None:
                return True
        return False

    def get_governor_verb(self, token):
        '''Get the verb governor of token. If the verb is part of a conjunction
         then the head of conjunction is returned.

        Args:
            token: A Token instance.

        Returns:
            The governor verb if it exists or None.
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

    def get_governor_pos(self, token, pos):
        '''Get the governor part-of-speech of token.

        Args:
            token: A Token instance.
            pos: The part-of-speech

        Returns:
            The governor part-of-speech if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if token.pos in pos:
                return token
            token = token.head
        if token.pos in pos:
            return token
        return None

    def get_governor_subj(self, token):
        '''Get the governor subject token.

        Args:
            token: A Token instance.

        Returns:
            The governor subject if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if token.dep == self._nlp.dep.NSUBJ:
                return token
            token = token.head
        return None

    def get_governor_obj(self, token):
        '''Get the governor object token.

        Args:
            token: A Token instance.

        Returns:
            The governor object if it exists or None.
        '''
        while token.dep != self._nlp.dep.ROOT:
            if token.dep in [self._nlp.dep.DOBJ, self._nlp.dep.IOBJ, self._nlp.dep.ACOMP]:
                return token
            token = token.head
        return None

    def get_first_of_conj(self, token):
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

    def find_clauses(self, sentence):
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
                if self.get_governor_subj(token) != state[1]:
                    state = stk.pop(-1)
                #else:
                #    excludeList.append(token)

            # 'NSUBJPASS', 'CSUBJ', 'CSUBJPASS', 'NOMCSUBJ', 'NOMCSUBJPASS'
            if token.dep  == self._nlp.dep.NSUBJ:
                self._process_as_subj(token)

            elif token.dep == self._nlp.dep.NSUBJPASS:
                if token.text.lower() in ['which', 'that']:
                    S = self.get_governor_subj(token)
                    if S is None:
                        self._process_as_subj(token)
                    else:
                        V = self.get_governor_verb(token)
                        if V is not None:
                            stk.append(state)
                            excludeList.append(token)
                            state = (states.NSUBJ_FIND, S)
                            self._process_as_subj(S, V)
                        else:
                            self._process_as_subj(token)
                else:
                    self._process_as_subj(token)

            # 'XCOMP','CCOMP','ATTR'
            elif token.pos == self._nlp.pos.ADP:
                if token.head.dep in [self._nlp.dep.ADVMOD, self._nlp.dep.QUANTMOD] and (token.head.i + 1) == token.i:
                    self._process_as_obj(token.head, self.get_governor_verb(token))
                else:
                    self._process_as_obj(token, self.get_governor_verb(token))

            elif token.dep in [self._nlp.dep.DOBJ, self._nlp.dep.IOBJ, self._nlp.dep.ACOMP, self._nlp.dep.ATTR]:
                self._process_as_obj(token)

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
                                          subjectSpan=SubtreeSpan(S, shallow=True), \
                                          verbSpan=SyntheticSpan('is'), \
                                          objectSpans=SubtreeSpan(token)))
                    S = None
            elif token.dep == self._nlp.dep.CONJ:
                # Find the first conjunction and label all other the same
                self._process_conj(token)

            elif token.dep == self._nlp.dep.CC:
                # Save for later. This will be excluded when we expand conjunctions
                if self._check_conj(token):
                    coordList.append(token)

            elif token.dep in [self._nlp.dep.XCOMP, self._nlp.dep.CCOMP]:
                # Xcomp can have a VERB or ADJ as a parent
                VA = self.get_governor_pos(token.head, [self._nlp.pos.VERB, self._nlp.pos.ADJ])
                if VA is not None:
                    if VA.dep == self._nlp.dep.ROOT:
                        # OK token will be used as is
                        V = VA
                        VA = token
                    else:
                        # TODO: can we further decompose xcomp
                        V = self.get_governor_verb(VA.head)
                        if V is None: continue
                    if not self._map.insert_new(V, [V, VA]):
                        if VA not in self._map.lookup(V):
                            self._map.append(V, VA)

        for k, m in self._map:
            if m is None or self._nlp.get_type_name(m[0].dep) != 'S': continue
            type = ''
            for tok in m:
                type += self._nlp.get_type_name(tok.pos) + self._nlp.get_type_name(tok.dep)

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

