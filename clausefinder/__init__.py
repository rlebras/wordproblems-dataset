from googlenlp import DependencyTrees

class Clause(object):
    def __init__(self, tokenIndexes, deptree):
        self._tokenIndexes = tokenIndexes
        self._depTree = deptree

    def __str__(self):
        txt = ""
        for i in self._tokenIndexes:
            txt += " " + self._depTree.tokens["text"]["content"]
        return txt.lstrip()

    def get(self):
        txt = [ ]
        for i in self._tokenIndexes:
            txt.append(self._depTree.tokens["text"]["content"])
        return txt

class ClauseDetector(object):
    def __init__(self, deptree):
        self._depTree = deptree