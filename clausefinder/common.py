#import googlenlp


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

    def insertNew(self, key, value):
        '''Insert value at key if the key is not mapped else do nothing.

        Args:
            key: An instance of Token.
            value: The value associated with key.

        Returns:
            True if the inserted, false if not.
        '''
        if self._tokMap[key.idx] >= self._tokLimit or self._map[self._tokMap[key.idx]][0] != key.idx:
            self._tokMap[key.idx] = self._tokLimit
            if self._tokLimit < len(self._map):
                self._map[self._tokLimit] = (key.idx, value)
            else:
                assert self._tokLimit == len(self._map)
                self._map.append((key.idx, value))
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
            # O(N) for reset, if deep is False then O(1)
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
        if not self.insertNew(key, [value]):
            self._map[self._tokMap[key.idx]][1].append(value)

    def extend(self, key, value):
        '''Extent an the value list associated with key.

        Args:
            key: The key. If the key does not exists value is added at key. if
                the key does exist value is appended to the value list at key.
            value: An instance of Token or a list of Token instances.
        '''
        if not self.insertNew(key, [value]):
            self._map[self._tokMap[key.idx]][1].extend(value)

    def lookup(self, key):
        '''Get the value at key.

        Args:
            key: An instance of Token.

        Returns:
             The value at key.
        '''
        if self._tokMap[key.idx] < self._tokLimit and self._map[self._tokMap[key.idx]][0] == key.idx:
            return self._map[self._tokMap[key.idx]][1]

    def replace(self, key, value):
        '''Replace the current value at key with a new value.

        Args:
            key: An instance of Token.
            value: The new value.
        '''
        if self._tokMap[key.idx] < self._tokLimit and self._map[self._tokMap[key.idx]][0] == key.idx:
            # map items are a tuple so keep list reference
            L = self._map[self._tokMap[key.idx]][1]
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


