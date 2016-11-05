from testdata import PROBLEMS
from testdata import GOOGLE_PROBLEMS
import unittest
from clausefinder import ClauseFinder
from clausefinder import googlenlp

class GoogleTest(unittest.TestCase):

    def test0_JsonProblems(self):
        if GOOGLE_PROBLEMS is None:
            return
        i = -1
        for p in GOOGLE_PROBLEMS:
            i += 1
            doc = googlenlp.Doc(p['google'])
            cf = ClauseFinder(doc)
            clauses = []
            for sent in doc.sents:
                clauses.extend(cf.find_clauses(sent))
            self.assertEquals(len(clauses), len(p['clauses']))
            for expect,actual in zip(p['clauses'],clauses):
                self.assertEquals(expect['type'], actual.type)
                self.assertEquals(expect['text'], actual.text)

    def disabled_test1_TextProblems(self):
        nlp = googlenlp.GoogleNLP()
        for p in PROBLEMS:
            result = nlp.parse(p['sentence'])
            self.assertIsNotNone(result)
            doc = googlenlp.Doc(result)
            cf = ClauseFinder(doc)
            clauses = []
            for sent in doc.sents:
                clauses.extend(cf.find_clauses(sent))
            self.assertEquals(len(clauses), len(p['clauses']))
            for expect,actual in zip(p['clauses'],clauses):
                self.assertEquals(expect['type'], actual.type)
                self.assertEquals(expect['text'], actual.text)


def run_tests():
    unittest.main()


if __name__ == '__main__':
    unittest.main()
