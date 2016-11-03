from spacy.symbols import IDS as SPACY_IDS
from clausefinder.googlenlp.dep import _GOOGLE_DEP_NAMES

for dn in _GOOGLE_DEP_NAMES:
    depname = dn.lower();
    if SPACY_IDS.has_key(depname):
        exec ('%s = %i' % (dn, SPACY_IDS[depname]))

