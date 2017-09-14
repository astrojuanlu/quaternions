import unittest
from hypothesis import given
from hypothesis.strategies import floats

import numpy as np

from quaternions import Quaternion


class QuaternionTest(unittest.TestCase):
    # Schaub, Chapter 3
    schaub_example_dcm = np.array([[.892539, .157379, -.422618],
                                   [-.275451, .932257, -.23457],
                                   [.357073, .325773, .875426]])
    schaub_result = np.array([.961798, -.14565, .202665, .112505])

    def test_matrix_respects_product(self):
        q1 = Quaternion.exp(Quaternion(0, .1, .02, -.3))
        q2 = Quaternion.exp(Quaternion(0, -.2, .21, .083))
        np.testing.assert_allclose((q1 * q2).matrix, q1.matrix.dot(q2.matrix))

    def test_from_matrix(self):
        q = Quaternion.from_matrix(QuaternionTest.schaub_example_dcm)
        np.testing.assert_allclose(QuaternionTest.schaub_result, q.coordinates, atol=1e-5, rtol=0)

    def test_from_matrix_twisted(self):
        q = Quaternion.from_matrix(QuaternionTest.schaub_example_dcm * [-1, -1, 1])
        e1 = Quaternion(*QuaternionTest.schaub_result)
        expected = e1 * Quaternion(0, 0, 0, 1)
        np.testing.assert_allclose(expected.coordinates, q.coordinates, atol=1e-5, rtol=0)

    def test_from_rotation_vector_to_matrix(self):
        phi = np.array([-.295067, .410571, .227921])
        expected = np.array([
            [.892539, .157379, -.422618],
            [-.275451, .932257, -.23457],
            [.357073, .325773, .875426]])
        q = Quaternion.from_rotation_vector(phi)
        np.testing.assert_allclose(expected, q.matrix, atol=1e-5, rtol=0)

    def test_qmethod(self):
        frame_1 = np.array([[2 / 3, 2 / 3, 1 / 3], [2 / 3, -1 / 3, -2 / 3]])
        frame_2 = np.array([[0.8, 0.6, 0], [-0.6, 0.8, 0]])
        q = Quaternion.from_qmethod(frame_1.T, frame_2.T, np.ones(2))

        for a1 in np.arange(0, 1, .1):
            for a2 in np.arange(0, 1, .1):
                v1 = a1 * frame_1[0] + a2 * frame_1[1]
                v2 = a1 * frame_2[0] + a2 * frame_2[1]
                np.testing.assert_allclose(q.matrix.dot(v1), v2, atol=1e-10)

    def test_ra_dec_roll(self):
        for ra in np.linspace(-170, 180, 8):
            for dec in np.linspace(-90, 90, 8):
                for roll in np.linspace(10, 360, 8):

                    xyz = np.deg2rad(np.array([ra, dec, roll]))
                    c3, c2, c1 = np.cos(xyz)
                    s3, s2, s1 = np.sin(xyz)
                    expected = np.array([
                        [c2 * c3,               -c2 * s3,                 s2],       # noqa
                        [c1 * s3 + c3 * s1 * s2, c1 * c3 - s1 * s2 * s3, -c2 * s1],  # noqa
                        [s1 * s3 - c1 * c3 * s2, c3 * s1 + c1 * s2 * s3,  c1 * c2]   # noqa
                    ])

                    obtained = Quaternion.from_ra_dec_roll(ra, dec, roll)

                    np.testing.assert_allclose(expected, obtained.matrix, atol=1e-15)

    def test_to_rdr(self):
        for ra in np.linspace(-170, 170, 8):
            for dec in np.linspace(-88, 88, 8):
                for roll in np.linspace(-170, 170, 8):
                    q = Quaternion.from_ra_dec_roll(ra, dec, roll)

                    np.testing.assert_allclose([ra, dec, roll], q.ra_dec_roll)

    def test_average_easy(self):
        q1 = Quaternion(1, 0, 0, 0)
        q2 = Quaternion(-1, 0, 0, 0)
        avg = Quaternion.average(q1, q2)

        np.testing.assert_allclose(q1.coordinates, avg.coordinates)

    def test_average_mild(self):
        q1 = Quaternion.exp(Quaternion(0, .1, .3, .7))
        quats_l = []
        quats_r = []
        for i in np.arange(-.1, .11, .05):
            for j in np.arange(-.1, .11, .05):
                for k in np.arange(-.1, .11, .05):
                    q = Quaternion.exp(Quaternion(0, i, j, k))
                    quats_l.append(q1 * q)
                    quats_r.append(q * q1)

        avg_l = Quaternion.average(*quats_l)
        avg_r = Quaternion.average(*quats_r)
        np.testing.assert_allclose(q1.coordinates, avg_l.coordinates)
        np.testing.assert_allclose(q1.coordinates, avg_r.coordinates)

    def test_optical_axis_first(self):
        v1 = np.array([.02, .01, .99])
        v2 = np.array([-.01, .02, .99])
        oaf = Quaternion.OpticalAxisFirst()
        np.testing.assert_allclose([.99, -.02, -.01], oaf.matrix.dot(v1))
        np.testing.assert_allclose([.99, .01, -.02], oaf.matrix.dot(v2))

    def test_distance(self):
        q = Quaternion.from_rotation_vector([.1, .2, .3])

        for rot_x in np.linspace(-np.pi, np.pi, 7):
            for rot_y in np.linspace(-np.pi / 2, np.pi / 2, 3):
                for rot_z in np.linspace(-np.pi / 2, np.pi / 2, 2):

                    rotation = [rot_x, rot_y, rot_z]
                    rot_quat = Quaternion.from_rotation_vector(rotation)
                    q_rot = q * rot_quat

                    expected = np.linalg.norm(rotation) % (2 * np.pi)
                    if expected > np.pi:
                        expected = 2 * np.pi - expected

                    self.assertAlmostEqual(expected, q.distance(q_rot))


class ParameterizedTests(unittest.TestCase):

    @given(floats(min_value=-180, max_value=180),
           floats(min_value=-90, max_value=90),
           floats(min_value=0, max_value=360))
    def test_quat_ra_dec_roll(self, ra, dec, roll):
        q = Quaternion.from_ra_dec_roll(ra, dec, 2.)
        ob_ra, ob_dec, ob_roll = q.ra_dec_roll
        assert abs(ob_dec - dec) < 1e-8
        assert abs(ob_ra - ra) < 1e-8
        

    @given(floats(min_value=-2, max_value=2),
           floats(min_value=-2, max_value=2),
           floats(min_value=-2, max_value=2))
    def test_quat_rotation_vector(self, rx, ry, rz):
        rot = np.array([rx, ry, rz])
        q = Quaternion.from_rotation_vector(rot)
        distance = np.linalg.norm(rot - q.rotation_vector)

        assert (distance % 2 * np.pi) < 1e-8
