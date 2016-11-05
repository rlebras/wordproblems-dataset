from spacy.en import English  # NLP with spaCy https://spacy.io
from spacy.symbols import IDS as SPACY_IDS
from clausefinder.googlenlp.dep import _GOOGLE_DEP_NAMES

NLP = English() # will take some time to load


_NO_GOOGLE_DEP_EQUIV = [
    'agent',
    'complm',
    'hyph',
    'hmod',
    'infmod',
    'intj',
    'meta',
    'nmod',
    'oprd',
    'possessive',
]

_GOOGLE_DEP_EQUIV = {
    'UNKNOWN': None,
    'ABBREV': None,
    'ADVPHMOD': None,
    'AUXCAUS': None,
    'AUXVV': None,
    'COP': None,
    'DISCOURSE': None,
    'DISLOCATED': None,
    'DTMOD': None,
    'FOREIGN': None,
    'GOESWITH': None,
    'KW': None,
    'LIST': None,
    'MWE': None,
    'MWV': None,
    'NOMC': None,
    'NOMCSUBJ': None,
    'NOMCSUBJPASS': None,
    'NUMC': None,
    'P': 'punct',
    'POSTNEG': None,
    'PRECOMP': None,
    'PREDET': None,
    'PREF': None,
    'PRONL': None,
    'PS': None,
    'RCMODREL': None,
    'RDROP': None,
    'REF': None,
    'REMNANT': None,
    'REPARANDUM': None,
    'SNUM': None,
    'SUFF': None,
    'SUFFIX': None,
    'TITLE': None,
    'TMOD': None,
    'TOPIC': None,
    'VMOD': None,
    'VOCATIVE': None
}


for depname in _GOOGLE_DEP_NAMES:
    dn = depname.lower()
    try:
        if SPACY_IDS.has_key(dn):
            exec ('%s = %i' % (depname, NLP.vocab.strings[dn]))
        elif _GOOGLE_DEP_EQUIV.has_key(depname) and _GOOGLE_DEP_EQUIV[depname] is not None:
            exec ('%s = %i' % (depname, NLP.vocab.strings[ _GOOGLE_DEP_EQUIV[depname] ]))
    except:
        pass


# See issue: https://github.com/explosion/spaCy/issues/607
ROOT = NLP.vocab.strings['ROOT']
