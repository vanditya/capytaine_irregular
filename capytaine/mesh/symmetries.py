#!/usr/bin/env python
# coding: utf-8
"""Special meshes with symmetries, useful to speed up the computations."""
# This file is part of "Capytaine" (https://github.com/mancellin/capytaine).
# It has been written by Matthieu Ancellin and is released under the terms of the GPLv3 license.

import logging

import numpy as np

from capytaine.mesh.mesh import Mesh
from capytaine.mesh.meshes_collection import CollectionOfMeshes
from capytaine.tools.geometry import Axis, Plane, Oz_axis, inplace_transformation

LOG = logging.getLogger(__name__)


class SymmetricMesh(CollectionOfMeshes):
    pass


class ReflectionSymmetry(SymmetricMesh):
    def __new__(cls, half, plane, name=None):
        """A mesh with one vertical symmetry plane.

        Parameters
        ----------
        half : Mesh or CollectionOfMeshes
            a mesh describing half of the body
        plane : Plane
            the symmetry plane across which the half body is mirrored
        name :str, optional
            a name for the mesh
        """
        assert isinstance(half, Mesh) or isinstance(half, CollectionOfMeshes)
        assert isinstance(plane, Plane)
        assert plane.normal[2] == 0  # Only vertical reflection planes are supported

        other_half = half.mirror(plane, inplace=False, name=f"mirror_of_{half.name}")

        self = super().__new__(cls, (half, other_half))

        self.plane = plane.copy()

        if name is None:
            self.name = CollectionOfMeshes.format_name(self, half.name)
        else:
            self.name = name

        LOG.info(f"New mirror symmetric mesh: {self.name}.")

        return self

    @property
    def half(self):
        return self[0]

    def tree_view(self, fold_symmetry=True, **kwargs):
        if fold_symmetry:
            return (self.name + '\n' + ' ├─' + self.half.tree_view().replace('\n', '\n │ ') + '\n'
                    + f" └─mirrored copy of the above {self.half.name}")
        else:
            return CollectionOfMeshes.tree_view(self, **kwargs)

    def __deepcopy__(self, *args):
        return ReflectionSymmetry(self.half.copy(), self.plane, name=self.name)

    def join_meshes(*meshes, name=None):
        assert all(isinstance(mesh, ReflectionSymmetry) for mesh in meshes), \
            "Only meshes with the same symmetry can be joined together."
        assert all(meshes[0].plane == mesh.plane for mesh in meshes), \
            "Only reflection symmetric meshes with the same reflection plane can be joined together."
        half_mesh = CollectionOfMeshes([mesh.half for mesh in meshes], name=f"half_of_{name}" if name is not None else None)
        return ReflectionSymmetry(half_mesh, plane=meshes[0].plane, name=name)

    @inplace_transformation
    def translate(self, vector):
        self.plane.translate(vector)
        CollectionOfMeshes.translate(self, vector)
        return self

    @inplace_transformation
    def rotate(self, axis, angle):
        self.plane.rotate(axis, angle)
        CollectionOfMeshes.rotate(self, axis, angle)
        return self

    @inplace_transformation
    def mirror(self, plane):
        self.plane.mirror(plane)
        CollectionOfMeshes.mirror(self, plane)
        return self


class TranslationalSymmetry(SymmetricMesh):
    def __new__(cls, mesh_slice, translation, nb_repetitions=1, name=None):
        """A mesh with a repeating pattern by translation.

        Parameters
        ----------
        mesh_slice : Mesh or CollectionOfMeshes
            the pattern that will be repeated to form the whole body
        translation : array(3)
            the vector of the translation
        nb_repetitions : int, optional
            the number of repetitions of the pattern (excluding the original one, default: 1)
        name : str, optional
            a name for the mesh
        """
        assert isinstance(mesh_slice, Mesh) or isinstance(mesh_slice, CollectionOfMeshes)
        assert isinstance(nb_repetitions, int)
        assert nb_repetitions >= 1

        translation = np.asarray(translation).copy()
        assert translation.shape == (3,)
        assert translation[2] == 0  # Only horizontal translation are supported.

        slices = [mesh_slice]
        for i in range(1, nb_repetitions+1):
            slices.append(mesh_slice.translated(vector=i*translation, name=f"repetition_{i}_of_{mesh_slice.name}"))

        self = super().__new__(cls, slices)

        self.translation = translation

        if name is None:
            self.name = CollectionOfMeshes.format_name(self, mesh_slice.name)
        else:
            self.name = name
        LOG.info(f"New translation symmetric mesh: {self.name}.")

        return self

    @property
    def first_slice(self):
        return self[0]

    def tree_view(self, fold_symmetry=True, **kwargs):
        if fold_symmetry:
            return (self.name + '\n' + ' ├─' + self.first_slice.tree_view().replace('\n', '\n │ ') + '\n'
                    + f" └─{len(self)-1} translated copies of the above {self.first_slice.name}")
        else:
            return CollectionOfMeshes.tree_view(self, **kwargs)

    def __deepcopy__(self, *args):
        return TranslationalSymmetry(self.first_slice.copy(), self.translation, nb_repetitions=len(self)-1, name=self.name)

    @inplace_transformation
    def translate(self, vector):
        CollectionOfMeshes.translate(self, vector)
        return self

    @inplace_transformation
    def rotate(self, axis, angle):
        self.translation = axis.rotation_matrix(angle) @ self.translation
        CollectionOfMeshes.rotate(self, axis, angle)
        return self

    @inplace_transformation
    def mirror(self, plane):
        self.translation -= 2 * (self.translation @ plane.normal) * plane.normal
        CollectionOfMeshes.mirror(self, plane)
        return self

    def join_meshes(*meshes, name=None):
        assert all(isinstance(mesh, TranslationalSymmetry) for mesh in meshes), \
            "Only meshes with the same symmetry can be joined together."
        assert all(np.allclose(meshes[0].translation, mesh.translation) for mesh in meshes), \
            "Only translation symmetric meshes with the same translation vector can be joined together."
        assert all(len(meshes[0]) == len(mesh) for mesh in meshes), \
            "Only symmetric meshes with the same number of elements can be joined together."
        mesh_strip = CollectionOfMeshes([mesh.first_slice for mesh in meshes], name=f"strip_of_{name}" if name is not None else None)
        return TranslationalSymmetry(mesh_strip, translation=meshes[0].translation, nb_repetitions=len(meshes[0])-1, name=name)


class AxialSymmetry(SymmetricMesh):
    def __new__(cls, mesh_slice, axis=Oz_axis, nb_repetitions=1, name=None):
        """A mesh with a repeating pattern by rotation.

        Parameters
        ----------
        mesh_slice : Mesh or CollectionOfMeshes
            the pattern that will be repeated to form the whole body
        axis : Axis, optional
            symmetry axis
        nb_repetitions : int, optional
            the number of repetitions of the pattern (excluding the original one, default: 1)
        name : str, optional
            a name for the mesh
        """
        assert isinstance(mesh_slice, Mesh) or isinstance(mesh_slice, CollectionOfMeshes)
        assert isinstance(nb_repetitions, int)
        assert nb_repetitions >= 1
        assert isinstance(axis, Axis)

        if not axis == Oz_axis:
            LOG.warning("Initialization of an axi-symmetric mesh along another axis than Oz. "
                        "It may not be useful for the resolution of the BEM problem")

        slices = [mesh_slice]
        for i in range(1, nb_repetitions+1):
            slices.append(mesh_slice.rotated(axis, angle=2*i*np.pi/(nb_repetitions+1),
                                       name=f"rotation_{i}_of_{mesh_slice.name}"))

        self = super().__new__(cls, slices)

        self.axis = axis.copy()

        if name is None:
            self.name = CollectionOfMeshes.format_name(self, mesh_slice.name)
        else:
            self.name = name
        LOG.info(f"New rotation symmetric mesh: {self.name}.")

        return self

    @staticmethod
    def from_profile(profile,
                     z_range=np.linspace(-5, 0, 20),
                     axis=Oz_axis,
                     nphi=20,
                     name=None):
        """Return a floating body using the axial symmetry.
        The shape of the body can be defined either with a function defining the profile as [f(z), 0, z] for z in z_range.
        Alternatively, the profile can be defined as a list of points.
        The number of vertices along the vertical direction is len(z_range) in the first case and profile.shape[0] in the second case.

        Parameters
        ----------
        profile : function(float → float)  or  array(N, 3)
            define the shape of the body either as a function or a list of points.
        z_range: array(N), optional
            used only if the profile is defined as a function.
        axis : Axis
            symmetry axis
        nphi : int, optional
            number of vertical slices forming the body
        name : str, optional
            name of the generated body (optional)

        Returns
        -------
        AxialSymmetry
            the generated mesh
        """

        if name is None:
            name = "axisymmetric_mesh"

        if callable(profile):
            x_values = [profile(z) for z in z_range]
            profile_array = np.stack([x_values, np.zeros(len(z_range)), z_range]).T
        else:
            profile_array = np.asarray(profile)

        assert len(profile_array.shape) == 2
        assert profile_array.shape[1] == 3

        n = profile_array.shape[0]
        angle = 2 * np.pi / nphi

        rotated_profile = Mesh(profile_array, np.zeros((0, 4)), name="rotated_profile_mesh")
        rotated_profile.rotate_z(angle)

        nodes_slice = np.concatenate([profile_array, rotated_profile.vertices])
        faces_slice = np.array([[i, i+n, i+n+1, i+1] for i in range(n-1)])
        body_slice = Mesh(nodes_slice, faces_slice, name=f"slice_of_{name}_mesh")
        body_slice.merge_duplicates()
        body_slice.heal_triangles()

        return AxialSymmetry(body_slice, axis=axis, nb_repetitions=nphi-1, name=name)

    @property
    def first_slice(self):
        return self[0]

    def tree_view(self, fold_symmetry=True, **kwargs):
        if fold_symmetry:
            return (self.name + '\n' + ' ├─' + self.first_slice.tree_view().replace('\n', '\n │ ') + '\n'
                    + f" └─{len(self)-1} rotated copies of the above {self.first_slice.name}")
        else:
            return CollectionOfMeshes.tree_view(self, **kwargs)

    def __deepcopy__(self, *args):
        return AxialSymmetry(self.first_slice.copy(), axis=self.axis.copy(), nb_repetitions=len(self)-1, name=self.name)

    def join_meshes(*meshes, name=None):
        assert all(isinstance(mesh, AxialSymmetry) for mesh in meshes), \
            "Only meshes with the same symmetry can be joined together."
        assert all(meshes[0].axis == mesh.axis for mesh in meshes), \
            "Only axisymmetric meshes with the same symmetry axis can be joined together."
        assert all(len(meshes[0]) == len(mesh) for mesh in meshes), \
            "Only axisymmetric meshes with the same number of elements can be joined together."
        mesh_slice = CollectionOfMeshes([mesh.first_slice for mesh in meshes], name=f"slice_of_{name}" if name is not None else None)
        return AxialSymmetry(mesh_slice, axis=meshes[0].axis, nb_repetitions=len(meshes[0])-1, name=name)

    @inplace_transformation
    def translate(self, vector):
        self.axis.translate(vector)
        CollectionOfMeshes.translate(self, vector)
        return self

    @inplace_transformation
    def rotate(self, other_axis, angle):
        self.axis.rotate(other_axis, angle)
        CollectionOfMeshes.rotate(self, other_axis, angle)
        return self

    @inplace_transformation
    def mirror(self, plane):
        self.axis.mirror(plane)
        CollectionOfMeshes.mirror(self, plane)
        return self
