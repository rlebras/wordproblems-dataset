from spacy.en import English  # NLP with spaCy https://spacy.io
from spacy.symbols import IDS as SPACY_IDS
from clausefinder.googlenlp.dep import _GOOGLE_DEP_NAMES

NLP = English() # will take some time to load

for depname in _GOOGLE_DEP_NAMES:
    dn = depname.lower()

    try:
        if SPACY_IDS.has_key(dn):
            exec ('%s = %i' % (depname, NLP.vocab.strings[dn]))
    except:
        pass

# I believe this is a bug but SpaCy root must use uppercase string.
# See issue: https://github.com/explosion/spaCy/issues/607
ROOT = NLP.vocab.strings['ROOT']