#!/usr/bin/env python
# coding: utf-8
"""Compute the potential and velocity of Airy wave."""
# This file is part of "capytaine" (https://github.com/mancellin/capytaine).
# It has been written by Matthieu Ancellin and is released under the terms of the GPLv3 license.

import numpy as np

from capytaine.bem.problems_and_results import DiffractionProblem


def airy_waves_potential(points, pb: DiffractionProblem, convention="Nemoh"):
    """Compute the potential for Airy waves at a given point (or array of points).

    Parameters
    ----------
    points: array of shape (3) or (N x 3)
        coordinates of the points in which to evaluate the potential.
    pb: DiffractionProblem
        problem with the environmental conditions (g, rho, ...) of interest
    convention: str, optional
        convention for the incoming wave field. Accepted values: "Nemoh", "WAMIT".

    Returns
    -------
    array of shape (1) or (N x 1)
        The potential
    """
    assert convention.lower() in ["nemoh", "wamit"], \
        "Convention for wave field should be either Nemoh or WAMIT."

    x, y, z = points.T
    k = pb.wavenumber
    h = pb.depth
    wbar = x*np.cos(pb.angle) + y*np.sin(pb.angle)

    if 0 <= k*h < 20:
        cih = np.cosh(k*(z+h))/np.cosh(k*h)
        # sih = np.sinh(k*(z+h))/np.cosh(k*h)
    else:
        cih = np.exp(k*z)
        # sih = np.exp(k*z)

    if convention.lower() == "wamit":
        return  1j*pb.g/pb.omega * cih * np.exp(-1j * k * wbar)
    else:
        return -1j*pb.g/pb.omega * cih * np.exp(1j * k * wbar)


def airy_waves_velocity(points, pb: DiffractionProblem, convention="Nemoh"):
    """Compute the fluid velocity for Airy waves at a given point (or array of points).

    Parameters
    ----------
    points: array of shape (3) or (N x 3)
        coordinates of the points in which to evaluate the potential.
    pb: DiffractionProblem
        problem with the environmental conditions (g, rho, ...) of interest
    convention: str, optional
        convention for the incoming wave field. Accepted values: "Nemoh", "WAMIT".

    Returns
    -------
    array of shape (3) or (N x 3)
        the velocity vectors
    """
    assert convention.lower() in ["nemoh", "wamit"], \
        "Convention for wave field should be either Nemoh or WAMIT."

    x, y, z = points.T
    k = pb.wavenumber
    h = pb.depth

    wbar = x*np.cos(pb.angle) + y*np.sin(pb.angle)

    if 0 <= k*h < 20:
        cih = np.cosh(k*(z+h))/np.cosh(k*h)
        sih = np.sinh(k*(z+h))/np.cosh(k*h)
    else:
        cih = np.exp(k*z)
        sih = np.exp(k*z)

    v = pb.g*k/pb.omega * \
        np.exp(1j * k * wbar) * \
        np.array([np.cos(pb.angle)*cih, np.sin(pb.angle)*cih, -1j*sih])

    if convention.lower() == "wamit":
        return np.conjugate(v.T)
    else:
        return v.T


def froude_krylov_force(pb: DiffractionProblem, convention="Nemoh"):
    pressure = -1j * pb.omega * pb.rho * airy_waves_potential(pb.body.mesh.faces_centers, pb, convention=convention)
    forces = {}
    for dof in pb.influenced_dofs:
        # Scalar product on each face:
        normal_dof_amplitude_on_face = np.sum(pb.body.dofs[dof] * pb.body.mesh.faces_normals, axis=1)
        # Sum over all faces:
        forces[dof] = np.sum(pressure * normal_dof_amplitude_on_face * pb.body.mesh.faces_areas)
    return forces