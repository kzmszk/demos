"""registry of the 三十三間堂 statues: id -> Model factory"""
from . import statues_kannon as K

REGISTRY = {
    'kannon_standing_a': lambda: K.kannon_standing('a'),
    'kannon_standing_b': lambda: K.kannon_standing('b'),
    'kannon_standing_c': lambda: K.kannon_standing('c'),
}
REGISTRY['kannon_seated'] = K.kannon_seated
from . import statues_demons as Dm
REGISTRY['fujin'] = Dm.fujin
REGISTRY['raijin'] = Dm.raijin
from . import statues_attendants as At
for _sid, _sp in At.by_id().items():
    REGISTRY[_sid] = (lambda sp=_sp: At.attendant(sp))
from . import statues_guardians as Gu
for _sid, _sp in Gu.by_id().items():
    REGISTRY[_sid] = (lambda sp=_sp: Gu.guardian(sp))
from . import statues_narayana as Na
REGISTRY['narayana_kengo'] = Na.narayana
from . import statues_fujinraijin as FR
REGISTRY['fujin'] = FR.fujin
REGISTRY['raijin'] = FR.raijin
from . import statues_misshaku as Ms
REGISTRY['misshaku_kongoshi'] = Ms.misshaku
