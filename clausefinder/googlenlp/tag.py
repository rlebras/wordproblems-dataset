# Generic tag class used for a part-of-speech or a dependency-relation

class ConstantTag(object):
    '''Constant Tag class'''
    def __init__(self, id, name):
        self._id = id
        self._name = name

    def __eq__(self, other):
        return isinstance(other, ConstantTag) and other._id == self._id

    def __ne__(self, other):
        return not isinstance(other, ConstantTag) or other._id != self._id

    def __lt__(self, other):
        return other._id < self._id

    def __gt__(self, other):
        return other._id > self._id

    def __le__(self, other):
        return other._id <= self._id

    def __ge__(self, other):
        return other._id >= self._id

    def __hash__(self):
        return (self._id << 5) ^ (self.id >> 27)

    @property
    def id(self):
        return self._id

    @property
    def text(self):
        return self._name


