import unittest
import random
import six
from hypothesis import given, strategies as st
import functools

if six.PY2:
    import dice
else:
    from .import dice


# all hail stochastic testing
CASE_ITERATIONS = 10000
MAX_DIE_SIZE = 20
MAX_N_DICE = 20


# helpers for randomization
def random_ndice(upper_limit=MAX_N_DICE):
    return random.randint(1, upper_limit) + 1


def random_size():
    return random.randint(1, MAX_DIE_SIZE+1)


@functools.lru_cache()
def faces_from_size(x_size=MAX_DIE_SIZE):
    return range(1, x_size+1)


def random_faces(x_size=MAX_DIE_SIZE):
    return faces_from_size(random.randint(2, x_size+1))


def random_mod(limit=MAX_DIE_SIZE):
    return random.randint(1, limit+1)


# cases
class DieResultInFaces(unittest.TestCase):
    """
    A Die object should always return values in
    its die faces, specified at init.
    """

    def test(self):
        for x in range(CASE_ITERATIONS):
            f = random_faces()
            d = dice.Die(faces=f)
            d.roll()
            self.assertTrue(d.result in f)


class CheckRollNDX(unittest.TestCase):
    """
    Verifies the roll_ndx() function generates a Roll with the appropriate
    dice.
    """
    @given(n_dice=st.sampled_from(range(1, 20)), x_size=st.sampled_from(range(2, 10000)))
    def test(self, n_dice, x_size):
        faces = faces_from_size(x_size)

        r = dice.roll_ndx(n_dice, x_size)

        # number of Dice in Roll should be n_dice
        self.assertTrue(len(r.dice) == n_dice)

        for d in r.dice:
            # each Die in Roll should have a result in faces
            self.assertTrue(d.result in faces,
                            'roll_ndx({n}, {x}) contains {d} result {r} not in faces {f}'\
                            .format(n=n_dice, x=x_size, d=d, r=d.result, f=faces))

        # overall result should be between n_dice and n_dice * x_size
        lower_limit = n_dice
        self.assertTrue(r.total >= lower_limit,
                        'roll_ndx({n}, {x}) yielded result {r} with total {t} less than {l}'\
                        .format(n=n_dice, x=x_size, r=r.result, t=r.total, l=lower_limit))

        upper_limit = n_dice * x_size
        self.assertTrue(r.total <= upper_limit,
                        'roll_ndx({n}, {x}) yielded total {t} greater than {l}'\
                        .format(n=n_dice, x=x_size, r=r.result, t=r.total, l=upper_limit))


class NDXRollString(unittest.TestCase):
    """
    Check that the standard ndx roll string pattern (e.g. '6d6') is parsed
    correctly and generates valid results.
    """
    pattern = '{n}d{x}'

    # testing ndx
    def test(self):
        for x in range(CASE_ITERATIONS):
            n_dice = random_ndice()
            x_size = random_size()
            faces = faces_from_size(x_size)

            test_string = self.pattern.format(n=n_dice, x=x_size)
            r = dice.roll(test_string)

            # number of Dice in Roll should be n_dice
            self.assertTrue(len(r.dice) == n_dice)

            for d in r.dice:
                # each Die in Roll should have a result in faces
                self.assertTrue(d.result in faces,
                                'Parsed {s} contains {d} result {r} not in faces {f}'\
                                .format(s=test_string, d=d, r=d.result, f=faces))

            # overall result should be between n_dice and n_dice * x_size
            lower_limit = n_dice
            self.assertTrue(r.total >= lower_limit,
                            'Parsed {s} yielded result {r} with total {t} less than {l}'\
                            .format(s=test_string, r=r.result, t=r.total, l=lower_limit))

            upper_limit = n_dice * x_size
            self.assertTrue(r.total <= upper_limit,
                            'Parsed {s} yielded total {t} greater than {l}'\
                            .format(s=test_string, r=r.result, t=r.total, l=upper_limit))


class NDXwmodRollString(unittest.TestCase):
    """
    Check that a modified roll patter roll string pattern (e.g., '3d6+3') is
    parsed correctly and generates valid results.
    """
    pattern = '{n}d{x}{plusminus}{mod}'
    # testing ndx
    # TODO create hypothesis strategy for making dice expressions
    @given(n_dice=st.sampled_from(range(1, 20)), x_size=st.sampled_from(range(2, 10000)), mod=st.integers())
    def test(self, n_dice, x_size, mod):
        faces = faces_from_size(x_size)

        if mod >= 0:
            plusminus = "+"
        else:
            plusminus = ""

        test_string = self.pattern.format(n=n_dice,
                                          x=x_size,
                                          plusminus=plusminus,
                                          mod=mod)

        r = dice.roll(test_string)

        # number of Dice in Roll should be n_dice
        self.assertTrue(len(r.dice) == n_dice)

        for d in r.dice:
            # each Die in Roll should have a result in faces or faces*mod
            faces_w_mod = set(faces) | set(f+mod for f in faces)
            self.assertTrue(d.result in faces,
                            'Parsed {s} contains {d} result {r} not in faces(+mod) {f}'\
                            .format(s=test_string, d=d, r=d.result, f=faces_w_mod))

        # overall result should be between n_dice+mode and n_dice*x_size+mod
        lower_limit = n_dice + mod
        self.assertTrue(r.total >= lower_limit,
                        'Parsed {s} yielded result {r} with total {t} less than {l}'\
                        .format(s=test_string, r=r.result, t=r.total, l=lower_limit))

        upper_limit = n_dice * x_size + mod
        self.assertTrue(r.total <= upper_limit,
                        'Parsed {s} yielded result {r} with total {t} greater than {l}'\
                        .format(s=test_string, r=r.result, t=r.total, l=upper_limit))


def main():
    unittest.main()


if __name__ == '__main__':
    main()
