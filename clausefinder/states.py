import googlenlp

_dummyTag = googlenlp.tag.ConstantTag(0, 'DUMMY_TAG')

# Clause finder states
# State strings
_STATE_NAMES = [
    "ROOT_FIND",
    "NSUBJ_FIND"
]


for i in range(len(_STATE_NAMES)):
    exec('%s = googlenlp.tag.ConstantTag(%i, _STATE_NAMES[%i])' % (_STATE_NAMES[i], i, i))

