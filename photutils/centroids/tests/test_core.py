# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for the core module.
"""

import itertools

from astropy.modeling.models import Gaussian1D, Gaussian2D
import numpy as np
from numpy.testing import assert_allclose
import pytest

from ..core import (centroid_1dg, centroid_2dg, centroid_com, centroid_epsf,
                    fit_2dgaussian, gaussian1d_moments)
from ...psf import IntegratedGaussianPRF

try:
    # the fitting routines in astropy use scipy.optimize
    import scipy  # noqa
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


XCS = [25.7]
YCS = [26.2]
XSTDDEVS = [3.2, 4.0]
YSTDDEVS = [5.7, 4.1]
THETAS = np.array([30., 45.]) * np.pi / 180.
DATA = np.zeros((3, 3))
DATA[0:2, 1] = 1.
DATA[1, 0:2] = 1.
DATA[1, 1] = 2.


@pytest.mark.skipif('not HAS_SCIPY')
@pytest.mark.parametrize(
    ('xc_ref', 'yc_ref', 'x_stddev', 'y_stddev', 'theta'),
    list(itertools.product(XCS, YCS, XSTDDEVS, YSTDDEVS, THETAS)))
def test_centroids(xc_ref, yc_ref, x_stddev, y_stddev, theta):
    model = Gaussian2D(2.4, xc_ref, yc_ref, x_stddev=x_stddev,
                       y_stddev=y_stddev, theta=theta)
    y, x = np.mgrid[0:50, 0:47]
    data = model(x, y)

    xc, yc = centroid_com(data)
    assert_allclose([xc_ref, yc_ref], [xc, yc], rtol=0, atol=1.e-3)

    xc2, yc2 = centroid_1dg(data)
    assert_allclose([xc_ref, yc_ref], [xc2, yc2], rtol=0, atol=1.e-3)

    xc3, yc3 = centroid_2dg(data)
    assert_allclose([xc_ref, yc_ref], [xc3, yc3], rtol=0, atol=1.e-3)


@pytest.mark.skipif('not HAS_SCIPY')
@pytest.mark.parametrize(
    ('xc_ref', 'yc_ref', 'x_stddev', 'y_stddev', 'theta'),
    list(itertools.product(XCS, YCS, XSTDDEVS, YSTDDEVS, THETAS)))
def test_centroids_witherror(xc_ref, yc_ref, x_stddev, y_stddev, theta):
    model = Gaussian2D(2.4, xc_ref, yc_ref, x_stddev=x_stddev,
                       y_stddev=y_stddev, theta=theta)
    y, x = np.mgrid[0:50, 0:50]
    data = model(x, y)
    error = np.sqrt(data)

    xc2, yc2 = centroid_1dg(data, error=error)
    assert_allclose([xc_ref, yc_ref], [xc2, yc2], rtol=0, atol=1.e-3)

    xc3, yc3 = centroid_2dg(data, error=error)
    assert_allclose([xc_ref, yc_ref], [xc3, yc3], rtol=0, atol=1.e-3)


@pytest.mark.skipif('not HAS_SCIPY')
@pytest.mark.parametrize(
    ('xc_ref', 'yc_ref', 'x_stddev', 'y_stddev', 'theta'),
    list(itertools.product(XCS, YCS, XSTDDEVS, YSTDDEVS, THETAS)))
def test_centroids_oversampling(xc_ref, yc_ref, x_stddev, y_stddev, theta):
    model = Gaussian2D(2.4, xc_ref, yc_ref, x_stddev=x_stddev,
                       y_stddev=y_stddev, theta=theta)
    y, x = np.mgrid[0:50, 0:50]
    data = model(x, y)
    mask = np.zeros(data.shape, dtype=bool)
    data[10, 10] = 1.e5
    mask[10, 10] = True
    for oversampling in [4, (4, 6)]:
        if not hasattr(oversampling, '__len__'):
            _oversampling = (oversampling, oversampling)
        else:
            _oversampling = oversampling
        xc, yc = centroid_com(data, mask=mask, oversampling=oversampling)
        assert_allclose([xc, yc], [xc_ref / _oversampling[0], yc_ref / _oversampling[1]],
                        rtol=0, atol=1.e-3)


@pytest.mark.skipif('not HAS_SCIPY')
def test_centroids_withmask():
    xc_ref, yc_ref = 24.7, 25.2
    model = Gaussian2D(2.4, xc_ref, yc_ref, x_stddev=5.0, y_stddev=5.0)
    y, x = np.mgrid[0:50, 0:50]
    data = model(x, y)
    mask = np.zeros(data.shape, dtype=bool)
    data[10, 10] = 1.e5
    mask[10, 10] = True

    xc, yc = centroid_com(data, mask=mask)
    assert_allclose([xc, yc], [xc_ref, yc_ref], rtol=0, atol=1.e-3)

    xc2, yc2 = centroid_1dg(data, mask=mask)
    assert_allclose([xc2, yc2], [xc_ref, yc_ref], rtol=0, atol=1.e-3)

    xc3, yc3 = centroid_2dg(data, mask=mask)
    assert_allclose([xc3, yc3], [xc_ref, yc_ref], rtol=0, atol=1.e-3)


@pytest.mark.skipif('not HAS_SCIPY')
def test_centroids_withmask_nonbool():
    data = np.arange(16).reshape(4, 4)
    mask = np.zeros(data.shape)
    mask[0:2, :] = 1
    mask2 = np.array(mask, dtype=bool)

    xc1, yc1 = centroid_com(data, mask=mask)
    xc2, yc2 = centroid_com(data, mask=mask2)
    assert_allclose([xc1, yc1], [xc2, yc2])


@pytest.mark.skipif('not HAS_SCIPY')
@pytest.mark.parametrize('use_mask', [True, False])
def test_centroids_nan_withmask(use_mask):
    xc_ref, yc_ref = 24.7, 25.2
    model = Gaussian2D(2.4, xc_ref, yc_ref, x_stddev=5.0, y_stddev=5.0)
    y, x = np.mgrid[0:50, 0:50]
    data = model(x, y)
    data[20, :] = np.nan
    if use_mask:
        mask = np.zeros(data.shape, dtype=bool)
        mask[20, :] = True
    else:
        mask = None

    xc, yc = centroid_com(data, mask=mask)
    assert_allclose(xc, xc_ref, rtol=0, atol=1.e-3)
    assert yc > yc_ref

    xc2, yc2 = centroid_1dg(data, mask=mask)
    assert_allclose([xc2, yc2], [xc_ref, yc_ref], rtol=0, atol=1.e-3)

    xc3, yc3 = centroid_2dg(data, mask=mask)
    assert_allclose([xc3, yc3], [xc_ref, yc_ref], rtol=0, atol=1.e-3)


def test_centroid_com_mask():
    """Test centroid_com with and without an image_mask."""

    data = np.ones((2, 2)).astype(float)
    mask = [[False, False], [True, True]]
    centroid = centroid_com(data, mask=None)
    centroid_mask = centroid_com(data, mask=mask)
    assert_allclose([0.5, 0.5], centroid, rtol=0, atol=1.e-6)
    assert_allclose([0.5, 0.0], centroid_mask, rtol=0, atol=1.e-6)


@pytest.mark.skipif('not HAS_SCIPY')
def test_invalid_mask_shape():
    """
    Test if ValueError raises if mask shape doesn't match data
    shape.
    """

    data = np.zeros((4, 4))
    mask = np.zeros((2, 2), dtype=bool)

    with pytest.raises(ValueError):
        centroid_com(data, mask=mask)

    with pytest.raises(ValueError):
        centroid_1dg(data, mask=mask)

    with pytest.raises(ValueError):
        centroid_2dg(data, mask=mask)

    with pytest.raises(ValueError):
        gaussian1d_moments(data, mask=mask)


@pytest.mark.skipif('not HAS_SCIPY')
def test_invalid_error_shape():
    """
    Test if ValueError raises if error shape doesn't match data
    shape.
    """

    error = np.zeros((2, 2), dtype=bool)
    with pytest.raises(ValueError):
        centroid_1dg(np.zeros((4, 4)), error=error)

    with pytest.raises(ValueError):
        centroid_2dg(np.zeros((4, 4)), error=error)


def test_gaussian1d_moments():
    x = np.arange(100)
    desired = (75, 50, 5)
    g = Gaussian1D(*desired)
    data = g(x)
    result = gaussian1d_moments(data)
    assert_allclose(result, desired, rtol=0, atol=1.e-6)

    data[0] = 1.e5
    mask = np.zeros(data.shape).astype(bool)
    mask[0] = True
    result = gaussian1d_moments(data, mask=mask)
    assert_allclose(result, desired, rtol=0, atol=1.e-6)

    data[0] = np.nan
    mask = np.zeros(data.shape).astype(bool)
    mask[0] = True
    result = gaussian1d_moments(data, mask=mask)
    assert_allclose(result, desired, rtol=0, atol=1.e-6)


@pytest.mark.skipif('not HAS_SCIPY')
def test_fit2dgaussian_dof():
    data = np.ones((2, 2))
    with pytest.raises(ValueError):
        fit_2dgaussian(data)


@pytest.mark.skipif('not HAS_SCIPY')
def test_centroid_epsf():
    sigma = 0.5
    psf = IntegratedGaussianPRF(sigma=sigma)
    for oversampling in [4, (4, 6)]:
        if not hasattr(oversampling, '__len__'):
            _oversampling = (oversampling, oversampling)
        else:
            _oversampling = oversampling
        x = np.arange(1 + 25 * _oversampling[0]) / _oversampling[0]
        x0 = x[-1] / 2
        x -= x0
        y = np.arange(1 + 25 * _oversampling[1]) / _oversampling[1]
        y0 = y[-1] / 2
        y -= y0
        offsets = np.array([0.1, 0.03])
        data = psf.evaluate(x=x.reshape(1, -1), y=y.reshape(-1, 1), flux=1, x_0=offsets[0],
                            y_0=offsets[1], sigma=sigma)

        mask = np.zeros(data.shape, dtype=bool)
        mask[0, 0] = 1
        centers = centroid_epsf(data, mask=mask, oversampling=oversampling)
        assert_allclose(centers, offsets+x0, rtol=1e-3, atol=1e-2)


def test_centroid_exceptions():
    data = np.ones((5, 5), dtype=float)
    mask = np.zeros((4, 5), dtype=int)
    mask[2, 2] = 1

    # Test data and mask having the same shape
    with pytest.raises(ValueError):
        centroid_epsf(data, mask)

    with pytest.raises(ValueError):
        centroid_epsf(data, shift_val=-1)

    with pytest.raises(ValueError):
        centroid_epsf(data, oversampling=-1)
    with pytest.raises(ValueError):
        centroid_com(data, oversampling=-1)

    data = np.ones((21, 21), dtype=float)
    data[10, 10] = np.inf
    with pytest.raises(ValueError):
        centroid_epsf(data)
