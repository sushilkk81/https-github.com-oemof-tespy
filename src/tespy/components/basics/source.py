# -*- coding: utf-8

"""Module for class Source.


This file is part of project TESPy (github.com/oemof/tespy). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location tespy/components/basics/source.py

SPDX-License-Identifier: MIT
"""

import numpy as np

from tespy.components.component import Component


class Source(Component):
    r"""
    A flow originates from a Source.

    Parameters
    ----------
    label : str
        The label of the component.

    design : list
        List containing design parameters (stated as String).

    offdesign : list
        List containing offdesign parameters (stated as String).

    design_path : str
        Path to the components design case.

    local_offdesign : boolean
        Treat this component in offdesign mode in a design calculation.

    local_design : boolean
        Treat this component in design mode in an offdesign calculation.

    char_warnings : boolean
        Ignore warnings on default characteristics usage for this component.

    printout : boolean
        Include this component in the network's results printout.

    Example
    -------
    Create a source and specify a label.

    >>> from tespy.components import Source
    >>> so = Source('a labeled source')
    >>> so.component()
    'source'
    >>> so.label
    'a labeled source'
    """

    @staticmethod
    def component():
        return 'source'

    @staticmethod
    def outlets():
        return ['out1']

    @staticmethod
    def is_branch_source():
        return True

    def start_branch(self):
        outconn = self.outl[0]
        branch = {
            "connections": [outconn],
            "components": [self, outconn.target],
            "subbranches": {}
        }
        outconn.target.propagate_to_target(branch)

        return {outconn.label: branch}

    def start_fluid_wrapper_branch(self):
        outconn = self.outl[0]
        branch = {
            "connections": [outconn],
            "components": [self]
        }
        outconn.target.propagate_wrapper_to_target(branch)

        return {outconn.label: branch}

    @staticmethod
    def get_mandatory_constraints():
        return {}

    def exergy_balance(self, T0):
        r"""Exergy balance calculation method of a source.

        A source does not destroy or produce exergy. The value of
        :math:`\dot{E}_\mathrm{bus}` is set to the exergy of the mass flow to
        make exergy balancing methods more simple as in general a mass flow can
        be fuel, product or loss.

        Parameters
        ----------
        T0 : float
            Ambient temperature T0 / K.

        Note
        ----
        .. math::

            \dot{E}_\mathrm{bus} = \dot{E}_\mathrm{out}^\mathrm{PH}
        """
        self.E_P = np.nan
        self.E_F = np.nan
        self.E_bus = {
            "chemical": self.outl[0].Ex_chemical,
            "physical": self.outl[0].Ex_physical,
            "massless": 0
        }
        self.E_D = np.nan
        self.epsilon = self._calc_epsilon()


    """+F+F+F+F++++START++++F+F+F+F+    von Jubran"""
    def set_source_costs(self, c_tot=None):
        # convert units
        # input for c is $/GJ and input for Z is $/h
        unit_C = (3600 / 10 ** 9)
        unit_c = (10 ** 9 / 3600)

        if c_tot is not None:
            self.outl[0].c_tot = c_tot
            # calculate outlet
            self.outl[0].Ex_tot = self.outl[0].Ex_physical + self.outl[0].Ex_chemical
            self.outl[0].C_tot = self.outl[0].c_tot * self.outl[0].Ex_tot * unit_C

            # approx costs per exergy unit fot T, M, PH and CH
            self.outl[0].C_therm = self.outl[0].C_tot * (self.outl[0].Ex_therm / self.outl[0].Ex_tot)
            self.outl[0].C_mech = self.outl[0].C_tot * (self.outl[0].Ex_mech / self.outl[0].Ex_tot)
            self.outl[0].C_physical = self.outl[0].C_tot * (self.outl[0].Ex_physical / self.outl[0].Ex_tot)
            self.outl[0].C_chemical = self.outl[0].C_tot * (self.outl[0].Ex_chemical / self.outl[0].Ex_tot)

            self.outl[0].c_therm = self.outl[0].C_therm / self.outl[0].Ex_therm * unit_c if self.outl[0].Ex_therm != 0 else 0
            self.outl[0].c_mech = self.outl[0].C_mech / self.outl[0].Ex_mech * unit_c if self.outl[0].Ex_mech != 0 else 0
            self.outl[0].c_physical = self.outl[0].C_physical / self.outl[0].Ex_physical * unit_c if self.outl[0].Ex_physical != 0 else 0
            self.outl[0].c_chemical = self.outl[0].C_chemical / self.outl[0].Ex_chemical * unit_c if self.outl[0].Ex_chemical != 0 else 0

    def set_source_costs_standard(self):
        # determine source costs depending on material, temperature, ...
        return
    """+F+F+F+F++++END++++F+F+F+F+    von Jubran"""
