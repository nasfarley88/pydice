import json, operator, re
from random import choice

import six
if six.PY3:
    from functools import cmp_to_key

# ROLL_STRING_PATTERN = '(?P<n_dice>\d+)d(?P<x_size>\d+)(?P<keep>[\^v]{1}\d+)?(?P<mod>[+-]{1}\d+)?'
ROLL_STRING_PATTERN = re.compile('(?P<n_dice>\d+)d(?P<x_size>\d+)(?P<keep>[\^v]{1}\d+)?(?P<mod>[+-]{1}\d+)?')

DICE_PATTERN = re.compile(r'[+-]?\d+d\d+[v^]?\d*')
DICE_PARTS_PATTERN = re.compile('(?P<n_dice>\d+)d(?P<x_size>\d+)(?P<keep>[\^v]{1}\d+)?(?P<mod>[+-]{1}\d+)?')
MODIFIER_PATTERN = re.compile(r'[+-]\d+')


# for python 3 compatibility
def cmp(a, b):
    return (a > b) - (a < b)


class Die(object):
    def __init__(self, faces=range(1, 7), mod=0,
                 above_okay=False, below_okay=False,
                 name=None, raw=None, roll_now=False,
                 *args, **kwargs):
        """
        Represents a die and the results of rolling it.

        Arguments
        faces: list of possible results (faces on a die), each with an equal
            chance of being rolled

        mod: a function applied to the raw result of the roll

        above_okay: can mod make a result which is above the max in faces?

        below_okay: can mod make a result which is below the max in faces?

        name: optional

        roll_now: or wait for self.roll() to be called manually
        """
        self.faces = faces
        self.mod = mod
        self.above_okay = above_okay
        self.below_okay = False
        self._name = name
        self._raw = raw

        if roll_now:
            self.roll()

    def roll(self):
        self._raw = choice(self.faces)
        return self.result

    @property
    def result(self):
        if self._raw is not None:
            r = self._raw + self.mod
            if (r > self.high_face and not self.above_okay):
                return self.high_face
            elif (r < self.low_face and not self.below_okay):
                return self.low_face
            else:
                return r
        else:
            return None

    @property
    def name(self):
        if self._name:
            return self._name
        else:
            return str(self.__class__.__name__)

    @property
    def high_face(self):
        return sorted(self.faces)[-1]

    @property
    def low_face(self):
        return sorted(self.faces)[0]

    def __repr__(self):
        return '<{n}: faces={f}, result={r}>'.format(
            n=self.name,
            f=self.faces,
            r=self.result
            )


class DN(Die):
    def __init__(self, size, *args, **kwargs):
        super(DN, self).__init__(faces=range(1, size+1), *args, **kwargs)
        self._name = 'Die (d{size})'.format(size=size)


class Throw(object):
    def __init__(self, dice, roll_now=True, *args, **kwargs):
        """
        Simulates throwing one or more Die objects and exposes a list of the
        results.
        """
        self.dice = dice

        if roll_now:
            self.throw()

    @property
    def result(self):
        return [d.result for d in self.dice]

    def throw(self):
        [d.roll() for d in self.dice]


class Roll(object):
    def __init__(self,
                 dice,
                 plus_pip=False,
                 total_mod=0,
                 roll_now=True,
                 n_dice=None,
                 x_size=None,
                 *args,
                 **kwargs):
        self.plus_pip = plus_pip
        self.throw = Throw(dice, roll_now)
        self.total_mod = total_mod
        self.n_dice = n_dice
        self.x_size = x_size

        self._dropped_dice = []

    def evaluate(self, val, comp=operator.eq):
        return sum(1 if comp(r, val) else 0 for r in self.throw.result)

    @property
    def result(self):
        return {
            'sum': self.sum,
            'total': self.total,
            'faces': self.faces,
            'throw_mod': self.total_mod,
            }

    @property
    def dice(self):
        return self.throw.dice

    @property
    def raw_dice(self):
        return self.dice + self._dropped_dice

    @property
    def faces(self):
        f = lambda x, y: cmp(x.result, y.result)
        if six.PY3:
            return [d.result for d in sorted(self.dice, key=cmp_to_key(f))]
        else:
            return [d.result for d in sorted(self.dice, cmp=f)]

    @property
    def total(self):
        return self.sum + self.total_mod

    @property
    def sum(self):
        return sum(r for r in self.throw.result)

    @property
    def json(self):
        return json.dumps(self.result)

    def __repr__(self):
        return '<Roll: result={r}>'.format(r=self.result)


def ndx(n_dice, x_size):
    return [DN(x_size) for n in range(n_dice)]


def roll_ndx(n_dice, x_size=6, total_mod=0, plus_half=False):
    dice = ndx(n_dice, x_size)
    if plus_half:
        dice.append(Die(mod=lambda x: int(x/2)))

    return Roll(dice, total_mod=total_mod)


def parse_dice_group(string):
    """
    Takes a string description of a roll and returns list of Dice.

    Examples
        '1d6': roll a single six-sided die
        '3d6': roll three six-sided dice
        '3d6+1': roll three six-sided dice and add 1 to the total result
        '6d6^3': roll six six-sided dice and keep the 3 highest values

    """

    # TODO make this function neater (or at least better commented).
    if '+' in string:
        string = string.replace('+', '')
    elif '-' in string:
        raise NotImplementedError("Sorry, negative dice are not (yet!) supported")

    m = ROLL_STRING_PATTERN.match(string)
    d = m.groupdict()
    n_dice = int(d['n_dice'])
    x_size = int(d['x_size'])
    if d['mod'] is not None:
        mod = int(d['mod'])
    else:
        mod = 0

    # get the roll instance
    r = roll_ndx(n_dice, x_size, mod)
    r.n_dice = n_dice
    r.x_size = x_size

    # check to see if this is a "best of" roll
    # e.g., 6d6 but keep the top 3: 6d6^3
    if d['keep']:
        keep_n = int(d['keep'][1:])

        if d['keep'][0] == '^':
            # keep the top rolls
            f = lambda x, y: cmp(y.result, x.result)
        else:
            # keep the bottom rolls
            f = lambda x, y: cmp(x.result, y.result)

        if six.PY3:
            s = sorted(r.dice, key=cmp_to_key(f))
        else:
            s = sorted(r.dice, cmp=f)
        r._dropped_dice.extend(i for i in s[keep_n:])
        r.throw.dice = s[:keep_n]

    return r.dice


def add_modifiers(iter_of_modifiers):
    """
    Adds an iterable of string modifiers.

    E.g. ['+2', '-3'] -> -1

    """
    total = 0
    for m in iter_of_modifiers:
        if m[0] == '+':
            total += int(m[1:])
        elif m[0] == '-':
            total -= int(m[1:])
        else:
            raise SyntaxError("Not sure what is meant by '{}'".format(m))

    return total


def roll(string='1d6'):
    """
    Takes a string description of a roll and returns a fully-loaded Roll
    object.

    Examples
        '1d6': roll a single six-sided die
        '3d6': roll three six-sided dice
        '3d6+1': roll three six-sided dice and add 1 to the total result
        '6d6^3': roll six six-sided dice and keep the 3 highest values

    """

    # Ignore whitespace
    string = re.sub(r'\s+', '', string)

    dice_matches = DICE_PATTERN.findall(string)
    edited_string = DICE_PATTERN.sub("X", string)
    modifier_matches = MODIFIER_PATTERN.findall(edited_string)
    if not dice_matches and not modifier_matches:
        raise Exception("Error parsing roll from string '{0}'".format(string))

    dice = []
    for d in dice_matches:
        dice += parse_dice_group(d)

    total_mod = add_modifiers(modifier_matches)
    r = Roll(dice, total_mod=total_mod)
    return r
