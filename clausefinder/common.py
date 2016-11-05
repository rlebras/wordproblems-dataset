DELAY_SPACY_IMPORT = True

class ClauseFinderMap(object):
    '''Helper for ClauseFinder. Should be faster than a dictionary, especially
    for large documents, since clear, insert and lookup are done in O(1) time.
    '''

    def __init__(self, doc):
        '''Constructor

        Args:
            doc: A googlenlp.Doc or spacy.Doc instance
        '''
        #if not isinstance(doc, (googlenlp.Doc, spacynlp.Doc)):
        #    raise TypeError
        self._tokMap = [0] * len(doc)
        self._tokLimit = 0
        self._map = []

    def insert_new(self, key, value):
        '''Insert value at key if the key is not mapped else do nothing.

        Args:
            key: An instance of Token.
            value: The value associated with key.

        Returns:
            True if the inserted, false if not.
        '''
        if self._tokMap[key.i] >= self._tokLimit or self._map[self._tokMap[key.i]][0] != key.i:
            self._tokMap[key.i] = self._tokLimit
            if self._tokLimit < len(self._map):
                self._map[self._tokLimit] = (key.i, value)
            else:
                assert self._tokLimit == len(self._map)
                self._map.append((key.i, value))
            self._tokLimit += 1
            return True
        return False

    def clear(self, deep=True):
        '''Clears the map to an empty state.

        Args:
            deep: If true do a deep reset in O(N) time, else do a shallow reset
                in O(1) time.
        '''
        # Once fully debugged we can set default deep=False.
        if deep:
            for i in range(self._tokLimit):
                self._map[i] = None
        self._tokLimit = 0

    def append(self, key, value):
        '''Append an item to the value list associated with key.

        Args:
            key: The key. If the key does not exists value is added at key. if
                the key does exist value is appended to the value list at key.
            value: An instance of Token.
        '''
        if not self.insert_new(key, [value]):
            self._map[self._tokMap[key.i]][1].append(value)

    def extend(self, key, value):
        '''Extend the value list associated with key.

        Args:
            key: The key. If the key does not exists value is added at key. if
                the key does exist value is appended to the value list at key.
            value: An instance of Token or a list of Token instances.
        '''
        if not self.insert_new(key, [value]):
            self._map[self._tokMap[key.i]][1].extend(value)

    def lookup(self, key):
        '''Get the value at key.

        Args:
            key: An instance of Token.

        Returns:
             The value at key.
        '''
        if self._tokMap[key.i] < self._tokLimit and self._map[self._tokMap[key.i]][0] == key.i:
            return self._map[self._tokMap[key.i]][1]

    def replace(self, key, value):
        '''Replace the current value at key with a new value.

        Args:
            key: An instance of Token.
            value: The new value.
        '''
        if self._tokMap[key.i] < self._tokLimit and self._map[self._tokMap[key.i]][0] == key.i:
            # map items are a tuple so keep list reference
            L = self._map[self._tokMap[key.i]][1]
            del L[0:len(L)]
            L.extend(value)

    def __len__(self):
        # Iterable override
        return self._tokLimit

    def __getitem__(self, slice_i_j):
        # Iterable override
        if isinstance(slice_i_j, slice):
            return self._map(range(slice_i_j))
        return self._map[slice_i_j]

    def __iter__(self):
        # Iterable override
        for i in range(self._tokLimit):
            yield self._map[i]


class IndexSpan(object):
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
        return self._doc[i]

    def __iter__(self):
        for k in self._indexes:
            yield self._doc[k]

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
        txt = self._doc[self._indexes[0]].text
        for i in self._indexes[1:]:
            tok = self._doc[i]
            if tok.is_punct:
                txt += tok.text
            else:
                txt += ' ' + tok.text
        return txt

    @property
    def text_with_ws(self):
        return self.text


class SubtreeSpan(IndexSpan):
    '''View of a document. Specialization of IndexSpan.'''

    def __init__(self, doc, idx=None, removePunct=False, shallow=False):
        '''Constructor.

        Args:
            idx: A token index or a Token instance.
            removePunct: If True punctuation is excluded from the span.
            shallow: If shallow is a boolean and True then don't add dependent
                tokens to span. If shallow isa list of token indexes these are
                used as the adjacency for the token a idx.
        '''
        if idx is not None and isinstance(idx, (int,long)):
            indexes = [idx]
        else:
            idx = doc.i
            doc = doc.doc
            indexes = [idx]

        stk = None
        if isinstance(shallow, list):
            if len(shallow) > 0:
                stk = shallow
            shallow = False

        if not shallow:
            tok = doc[idx]
            if hasattr(tok, 'adj'):
                # Google document
                if stk is None:
                    stk = []
                    stk.extend(tok.adj)
                indexes.extend(stk)
                while len(stk) != 0:
                    tok = doc[stk.pop()]
                    stk.extend(tok.adj)
                    indexes.extend(tok.adj)

            else:
                # Spacy document
                if stk is None:
                    stk = [x.i for x in tok.children]
                indexes.extend(stk)
                while len(stk) != 0:
                    tok = doc[stk.pop()]
                    adj = [x.i for x in tok.children]
                    stk.extend(adj)
                    indexes.extend(adj)
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
        txt = '(%i,\"%s' % (self._rootIdx, self._doc[self._indexes[0]].text)
        for i in self._indexes[1:]:
            tok = self._doc[i]
            if tok.is_punct:
                txt += tok.text
            else:
                txt += ' ' + tok.text
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
    def i(self):
        '''Return the root index of the subtree span.

        Returns: A index onto the Token array.
        '''
        return self._rootIdx


class SyntheticSpan(object):
    '''View of a document. The class has a similar interface to spacy.Span
    '''

    def __init__(self, text):
        self._text = text

    def __len__(self):
        return 0

    def __getitem__(self, i):
        raise NotImplemented

    def __iter__(self):
        pass

    def union(self, other):
        raise NotImplemented

    def complement(self, other):
        raise NotImplemented

    def intersect(self, other):
        raise NotImplemented

    @property
    def text(self):
        return '\"%s\"' % self._text

    @property
    def text_with_ws(self):
        return self.text


