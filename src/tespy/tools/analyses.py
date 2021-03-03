# -*- coding: utf-8

"""Module for thermodynamic analyses.

The analyses module provides thermodynamic analysis tools for your simulation.
Different analysis classes are available:

- :py:class:`tespy.tools.analyses.ExergyAnalysis`


This file is part of project TESPy (github.com/oemof/tespy). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location tespy/tools/analyses.py

SPDX-License-Identifier: MIT
"""

import logging

import pandas as pd
from tabulate import tabulate

from tespy.tools import helpers as hlp
from tespy.tools.global_vars import err

# %%


class ExergyAnalysis:
    r"""
    Class for exergy analysis.

    Parameters
    ----------
    x : ndarray
        An array for the x-values of the lookup table. Number of x and y
        values must be identical.

    y : ndarray
        The corresponding y-values for the lookup table. Number of x and y
        values must be identical.

    extrapolate : boolean
        If :code:`True` linear extrapolation is performed when the x value is
        out of the defined value range.

    Note
    ----
    This class generates a lookup table from the given input data x and y,
    then performs linear interpolation. The x and y values may be specified by
    the user. There are some default characteristic lines for different
    components, see the :py:mod:`tespy.data` module. If you neither specify the
    method to use from the defaults nor specify x and y values, the
    characteristic line generated will be
    :code:`x = [0, 1], y = [1, 1]`.
    """

    def __init__(self, network, E_F, E_P, E_L=[], internal_busses=[]):
        r"""Exergy analysis class.

        - Calculate the values of physical exergy on all connections.
        - Calculate exergy balance for all components. The individual exergy
          balance methods are documented in the API-documentation of the
          respective components.

          - Components for which no exergy balance has yet been implemented,
            :code:`nan` (not defined) is assigned for fuel and product
            exergy as well as exergy destruction and exergetic efficiency.
          - Dissipative components do not have product exergy (:code:`nan`) per
            definition.

        - Calculate network fuel exergy and product exergy from data provided
          from the busses passed to this method.
        - Component fuel and product exergy of components passed within the
          busses of :code:`E_F`, :code:`E_P` and :code:`internal_busses` are
          adjusted to consider the bus conversion factor, too.
        - Calculate network exergetic efficiency.
        - Calculate exergy destruction ratios for components.

          - :math:`y_\mathrm{D}` compare the rate of exergy destruction in a
            component to the exergy rate of the fuel provided to the overall
            system.
          - :math:`y^*_\mathrm{D}` compare the component exergy destruction
            rate to the total exergy destruction rate within the system.

        Parameters
        ----------
        E_F : float
            List containing busses which represent fuel exergy input of the
            network, e.g. heat exchangers of the steam generator.

        E_P : list
            List containing busses which represent exergy production of the
            network, e.g. the motors and generators of a power plant.

        E_L : list
            Optional: List containing busses which represent exergy loss
            streams of the network to the ambient, e.g. flue gases of a gas
            turbine.

        internal_busses : list
            Optional: List containing internal busses that represent exergy
            transfer within your network but neither exergy production or
            exergy fuel, e.g. a steam turbine driven feed water pump. The
            conversion factors of the bus are applied to calculate exergy
            destruction which is allocated to the respective components.

        Note
        ----
        The nomenclature of the variables used in the exergy analysis is
        according to :cite:`Tsatsaronis2007`.

        .. math::

            \begin{split}
            E_{\mathrm{D},comp} = E_{\mathrm{F},comp} - E_{\mathrm{P},comp}
            \;& \\
            \varepsilon_{\mathrm{comp}} =
            \frac{E_{\mathrm{P},comp}}{E_{\mathrm{F},comp}} \;& \\
            E_{\mathrm{D}} = \sum_{comp} E_{\mathrm{D},comp} \;&
            \forall comp \in \text{ network components}\\
            E_{\mathrm{P}} = \sum_{comp} E_{\mathrm{P},comp} \;&
            \forall comp \in
            \text{ components of busses in E\_P if 'base': 'component'}\\
            E_{\mathrm{P}} = E_{\mathrm{P}} - \sum_{comp} E_{\mathrm{F},comp}
            \;& \forall comp \in
            \text{ components of busses in E\_P if 'base': 'bus'}\\
            E_{\mathrm{F}} = \sum_{comp} E_{\mathrm{F},comp} \;&
            \forall comp \in
            \text{ components of busses in E\_F if 'base': 'bus'}\\
            E_{\mathrm{F}} = E_{\mathrm{F}} - \sum_{comp} E_{\mathrm{P},comp}
            \;& \forall comp \in
            \text{ components of busses in E\_F if 'base': 'component'}\\
            E_{\mathrm{L}} = \sum_{comp} E_{\mathrm{D},comp} \;&
            \forall comp \in
            \text{ sinks of network components if parameter exergy='loss'}
            \end{split}

        The exergy balance of the network must be closed, meaning fuel exergy
        minus product exergy, exergy destruction and exergy losses must be
        zero (:math:`\Delta E_\text{max}=0.001`). If the balance is violated a
        warning message is prompted.

        .. math::

            |E_{\text{F}} - E_{\text{P}} - E_{\text{L}} - E_{\text{D}}| \leq
            \Delta E_\text{max}\\

            \varepsilon = \frac{E_{\text{P}}}{E_{\text{F}}}

            y_{\text{D},comp} =
            \frac{\dot{E}_{\text{D},comp}}{\dot{E}_{\text{F}}}\\
            y^*_{\text{D},comp} =
            \frac{\dot{E}_{\text{D},comp}}{\dot{E}_{\text{D}}}

        Example
        -------
        In this example a simple clausius rankine cycle is set up and an
        exergy analysis is performed after simulation of the power plant.
        Start by defining ambient state and genereral network setup.

        >>> from tespy.components import (CycleCloser, HeatExchangerSimple,
        ... Merge, Splitter, Valve, Compressor, Pump, Turbine)
        >>> from tespy.connections import Bus
        >>> from tespy.connections import Connection
        >>> from tespy.networks import Network
        >>> from tespy.tools import ExergyAnalysis

        >>> Tamb = 20
        >>> pamb = 1
        >>> fluids = ['water']
        >>> nw = Network(fluids=fluids)
        >>> nw.set_attr(p_unit='bar', T_unit='C', h_unit='kJ / kg',
        ... iterinfo=False)

        In order to show all functionalities available we use a feed water pump
        that is not driven electrically by a motor but instead internally by
        an own steam turbine. Therefore we split up the live steam from the
        steam generator and merge the streams after both steam turbines. For
        simplicity the steam generator and the condenser are modeled as simple
        heat exchangers.

        >>> cycle_close = CycleCloser('cycle closer')
        >>> splitter1 = Splitter('splitter 1')
        >>> merge1 = Merge('merge 1')
        >>> turb = Turbine('turbine')
        >>> fwp_turb = Turbine('feed water pump turbine')
        >>> condenser = HeatExchangerSimple('condenser')
        >>> fwp = Pump('pump')
        >>> steam_generator = HeatExchangerSimple('steam generator')

        >>> fs_in = Connection(cycle_close, 'out1', splitter1, 'in1')
        >>> fs_fwpt = Connection(splitter1, 'out1', fwp_turb, 'in1')
        >>> fs_t = Connection(splitter1, 'out2', turb, 'in1')
        >>> fwpt_ws = Connection(fwp_turb, 'out1', merge1, 'in1')
        >>> t_ws = Connection(turb, 'out1', merge1, 'in2')
        >>> ws = Connection(merge1, 'out1', condenser, 'in1')
        >>> cond = Connection(condenser, 'out1', fwp, 'in1')
        >>> fw = Connection(fwp, 'out1', steam_generator, 'in1')
        >>> fs_out = Connection(steam_generator, 'out1', cycle_close, 'in1')
        >>> nw.add_conns(fs_in, fs_fwpt, fs_t, fwpt_ws, t_ws, ws, cond,
        ... fw, fs_out)

        Next step is to set up the busses to later pass them according to the
        convetions in the list below:

        - E_F for fuel exergy
        - E_P for product exergy
        - internal_busses for internal energy transport
        - E_L for exergy loss streams to the ambient (sources and sinks go
          here, in case you use e.g. flue gases or air input)

        The first bus is for output power, which is only represented by the
        main steam turbine. The efficiency is set to 0.97. This bus will
        represent the product exergy.

        >>> power = Bus('power_output')
        >>> power.add_comps({'comp': turb, 'char': 0.97})

        The second bus is for driving the feed water pump. The total power of
        this bus is specified to be 0 in order to make sure, the power genrated
        by the secondary steam turbine is transferred to the feed water pump.
        For mechanical efficiency we choose 0.985 for both components, but
        we need to make sure, the :code:`'base'` of the feed water pump is
        :code:`'bus'` as the energy from the turbine drives the feed water
        pump.

        >>> fwp_power = Bus('feed water pump power', P=0)
        >>> fwp_power.add_comps(
        ... {'comp': fwp_turb, 'char': 0.985},
        ... {'comp': fwp, 'char': 0.985, 'base': 'bus'})

        The fuel exergy is the exergy input into the network which is
        represented by the heat input bus. Here again, as we have an energy
        input from outside of the network, the :code:`'base'` keyword must be
        specified to :code:`'bus'`.

        >>> heat = Bus('heat_input')
        >>> heat.add_comps({'comp': steam_generator, 'base': 'bus'})
        >>> nw.add_busses(power, fwp_power, heat)

        After setting up the busses, we specify the parameters for components
        and connections and start the simulation.

        >>> turb.set_attr(eta_s=0.9)
        >>> fwp_turb.set_attr(eta_s=0.87)
        >>> condenser.set_attr(pr=0.98)
        >>> fwp.set_attr(eta_s=0.75)
        >>> steam_generator.set_attr(pr=0.89)
        >>> fs_in.set_attr(m=10, p=120, T=600, fluid={'water': 1})
        >>> cond.set_attr(T=Tamb + 3, x=0)
        >>> nw.solve('design')

        To evaluate the exergy balance of the network, we create an instance of
        class :py:class:`tespy.tools.analyses.ExergyAnalysis`
        passing the network to analyse as well as the respective busses. To run
        the analysis, the ambient state is passed subsequently. The results of
        the analysis can be printed using the
        :py:meth:`tespy.tools.analyses.ExergyAnalysis.print_results` method.
        The exergy balance should be closed, if you set up your network
        analysis correctly. If not, an error is prompted.

        >>> ean = ExergyAnalysis(network=nw, E_F=[heat], E_P=[power],
        ... internal_busses=[fwp_power])
        >>> ean.analyse(pamb=pamb, Tamb=Tamb)
        >>> abs(round(ean.network_data['E_F'] - ean.network_data['E_P'] -
        ... ean.network_data['E_L'] - ean.network_data['E_D'], 3))
        0.0
        >>> ();ean.print_results();() # doctest: +ELLIPSIS
        (...)

        The exergy data of the passed busses, the network's components and
        connections as well as the network itself are stored as dataframes and
        therefore accessible for further investigation.

        >>> busses = ean.bus_data
        >>> components = ean.component_data
        >>> connections = ean.connection_data
        >>> network = ean.network_data

        Additionally, if you defined component groups for your components, the
        exergy data of these groups are accumulated and saved in an own
        DataFrame. Please note, that the exergy destruction values of the
        busses are allocated to the component groups in this case.

        >>> groups = ean.group_overview
        """
        if len(E_F) == 0:
            msg = ('Missing fuel exergy E_F of network.')
            logging.error(msg)
            raise hlp.TESPyNetworkError(msg)

        if len(E_P) == 0:
            msg = ('Missing product exergy E_P of network.')
            logging.error(msg)
            raise hlp.TESPyNetworkError(msg)

        self.nw = network
        self.E_F = E_F
        self.E_P = E_P
        self.E_L = E_L
        self.internal_busses = internal_busses

        self.reserved_fkt_groups = (
            ['E_P', 'E_F', 'E_D', 'E_L'] +
            [b.label for b in internal_busses + E_F + E_P + E_L])

        self.grassmann_diagram = {}

    def analyse(self, pamb, Tamb):
        """Analyse the network.

        Parameters
        ----------
        pamb : float
            Ambient pressure value for analysis, provide value in network's
            pressure unit.

        Tamb : float
            Ambient temperature value for analysis, provide value in network's
            temperature unit.
        """
        pamb_SI = hlp.convert_to_SI('p', pamb, self.nw.p_unit)
        Tamb_SI = hlp.convert_to_SI('T', Tamb, self.nw.T_unit)

        # reset data
        self.component_data = pd.DataFrame(
            columns=['E_F', 'E_P', 'E_D', 'epsilon', 'group'])
        self.bus_data = self.component_data.copy()
        self.connection_data = pd.DataFrame(columns=['e_PH', 'E_PH'])
        self.network_data = pd.Series(
            index=['E_F', 'E_P', 'E_D', 'E_L'], dtype='float64')
        self.network_data[:] = 0

        # physical exergy of connections
        for conn in self.nw.conns['object']:
            conn.get_physical_exergy(pamb_SI, Tamb_SI)
            self.connection_data.loc[conn.label] = [
                conn.ex_physical, conn.Ex_physical]

        self.group_data = {}
        for label in self.reserved_fkt_groups:
            self.group_data[label] = pd.Series(dtype='float64')

        # exergy balance of components
        for cp in self.nw.comps['object']:
            # save component information
            cp.exergy_balance(Tamb_SI)
            if not hasattr(cp, 'fkt_group'):
                cp.fkt_group = cp.label
            self.component_data.loc[cp.label] = [
                cp.E_F, cp.E_P, cp.E_D, cp.epsilon, cp.fkt_group]

            if cp.fkt_group in self.reserved_fkt_groups:
                msg = (
                    'The labels ' + ', '.join(self.reserved_fkt_groups) + ' '
                    'cannot be used by components (if no group was assigned) '
                    'or component groups in the exergy analysis. Found '
                    'component/group with name ' + cp.fkt_group + '.')
                raise ValueError(msg)
            elif cp.fkt_group not in self.group_data.keys():
                self.group_data[cp.fkt_group] = pd.Series(dtype='float64')

            self.evaluate_busses(cp)

        self.network_data.loc['E_D'] = (
            self.component_data['E_D'].sum() + self.bus_data['E_D'].sum())
        self.network_data.loc['E_F'] = abs(self.network_data.loc['E_F'])
        self.network_data.loc['E_P'] = abs(self.network_data.loc['E_P'])
        self.network_data.loc['epsilon'] = (
            self.network_data.loc['E_P'] / self.network_data.loc['E_F']
        )

        # calculate exergy destruction ratios for components/busses
        E_F = self.network_data.loc['E_F']
        E_D = self.network_data.loc['E_D']
        self.component_data['y_Dk'] = self.component_data['E_D'] / E_F
        self.component_data['y*_Dk'] = self.component_data['E_D'] / E_D
        self.bus_data['y_Dk'] = self.bus_data['E_D'] / E_F
        self.bus_data['y*_Dk'] = self.bus_data['E_D'] / E_D

        residual = abs(
            self.network_data.loc['E_F'] - self.network_data.loc['E_P'] -
            self.network_data.loc['E_D'] - self.network_data.loc['E_L'])

        if residual >= err ** 0.5:
            msg = (
                'The exergy balance of your network is not closed (residual '
                'value is ' + str(round(residual, 6)) + ', but should be '
                'smaller than ' + str(err ** 0.5) + '), you should check the '
                'component and network exergy data and check, if network is '
                'properly setup for the exergy analysis.')
            logging.error(msg)

        self.create_group_data()

    def evaluate_busses(self, cp):
        cp_on_num_busses = 0
        for b in self.E_F + self.E_P + self.internal_busses + self.E_L:
            if cp in b.comps.index:
                if cp_on_num_busses > 0:
                    msg = (
                        'The component ' + cp.label + ' is on multiple '
                        'busses in the exergy analysis. Make sure that no '
                        'component is connected to more than one of the '
                        'busses passed to the exergy_analysis method.')
                    logging.error(msg)
                    raise hlp.TESPyNetworkError(msg)

                if b.comps.loc[cp, 'base'] == 'bus':
                    self.bus_data.loc[cp.label, 'E_P'] = cp.E_bus
                    E_F = cp.E_bus / cp.calc_bus_efficiency(b)
                    self.bus_data.loc[cp.label, 'E_F'] = E_F
                    if b in self.E_F:
                        self.network_data.loc['E_F'] += E_F
                    elif b in self.E_P:
                        self.network_data.loc['E_P'] -= E_F
                    elif b in self.E_L:
                        self.network_data.loc['E_L'] -= E_F

                    if cp.fkt_group in self.group_data[b.label].index:
                        self.group_data[b.label].loc[cp.fkt_group] += E_F
                    else:
                        self.group_data[b.label].loc[cp.fkt_group] = E_F
                else:
                    E_P = cp.E_bus * cp.calc_bus_efficiency(b)
                    self.bus_data.loc[cp.label, 'E_P'] = E_P
                    self.bus_data.loc[cp.label, 'E_F'] = cp.E_bus
                    if b in self.E_F:
                        self.network_data.loc['E_F'] -= E_P
                    elif b in self.E_P:
                        self.network_data.loc['E_P'] += E_P
                    elif b in self.E_L:
                        self.network_data.loc['E_L'] += E_P

                    if b.label in self.group_data[cp.fkt_group].index:
                        self.group_data[cp.fkt_group].loc[b.label] += E_P
                    else:
                        self.group_data[cp.fkt_group].loc[b.label] = E_P

                self.bus_data.loc[cp.label, 'group'] = cp.fkt_group

                cp_on_num_busses += 1

        self.bus_data['E_D'] = self.bus_data['E_F'] - self.bus_data['E_P']
        self.bus_data['epsilon'] = self.bus_data['E_P'] / self.bus_data['E_F']

    def create_component_groups(self, cp):
        # groups for grassmann
        new_group = True
        try:
            if cp.fkt_group in self.group_data.keys():
                new_group = False
        except AttributeError:
            cp.fkt_group = cp.label

        if cp.fkt_group in self.reserved_fkt_groups:
            msg = (
                'The labels ' + ', '.join(self.reserved_fkt_groups) + ' '
                'cannot be used by components (if no group was assigned) '
                'or component groups in the exergy analysis.')
            raise ValueError(msg)

        # generate/update datastructure
        if new_group:
            self.group_data[cp.fkt_group] = {}
            self.group_data[cp.fkt_group]['components'] = [cp.label]
            self.group_data[cp.fkt_group]['targets'] = pd.Series(
                dtype='float64')
            self.group_data[cp.fkt_group]['targets'].loc['E_D'] = 0
        else:
            self.group_data[cp.fkt_group]['components'] += [cp.label]

        self.component_data.loc[cp.label, 'group'] = cp.fkt_group

    def create_group_data(self):

        for group in self.group_data.keys():
            E_D = 0
            for df in [self.component_data, self.bus_data]:
                E_D += df[df['group'] == group]['E_D'].sum()
            self.group_data[group].loc['E_D'] = E_D

        # establish connections for fuel exergy via bus balance
        for b in self.E_F:
            input_value = self.find_group_value_in_targets(b.label)
            self.group_data['E_F'].loc[b.label] = (
                self.group_data[b.label].sum() - input_value)

        # establish connections for product exergy via bus balance
        for b in self.E_P:
            input_value = self.find_group_value_in_targets(b.label)
            self.group_data[b.label].loc['E_P'] = (
                input_value - self.group_data[b.label].sum())

        # establish connections for exergy loss via bus balance
        for b in self.E_L:
            input_value = self.find_group_value_in_targets(b.label)
            self.group_data[b.label].loc['E_L'] = (
                input_value - self.group_data[b.label].sum())

        for fkt_group, data in self.group_data.items():
            comps = self.component_data[
                self.component_data['group'] == fkt_group].index
            for comp in comps:
                comp_obj = self.nw.get_comp(comp)
                sources = self.nw.conns[self.nw.conns['source'] == comp_obj]
                for conn in sources['object']:
                    if conn.target.label not in comps:
                        target_group = self.find_comp_in_groups(
                            conn.target.label, fkt_group)
                        target_value = conn.Ex_physical
                        if target_group in data.index:
                            self.group_data[fkt_group].loc[target_group] += (
                                target_value)
                        else:
                            self.group_data[fkt_group].loc[target_group] = (
                                target_value)

        self.group_overview = pd.DataFrame(columns=['E_F', 'E_P', 'E_D'])
        for fkt_group in self.component_data['group'].unique():
            self.group_overview.loc[fkt_group, 'E_F'] = (
                self.find_group_value_in_targets(fkt_group))
            self.group_overview.loc[fkt_group, 'E_D'] = (
                self.group_data[fkt_group].loc['E_D'])

        self.group_overview['E_P'] = (
            self.group_overview['E_F'] - self.group_overview['E_D'])
        self.group_overview['epsilon'] = (
            self.group_overview['E_P'] / self.group_overview['E_F'])
        self.group_overview['y_Dk'] = (
            self.group_overview['E_D'] / self.network_data.loc['E_F'])
        self.group_overview['y*_Dk'] = (
            self.group_overview['E_D'] / self.network_data.loc['E_D'])

    def find_group_value_in_targets(self, group_label):
        """"""
        value = 0
        for fkt_group, data in self.group_data.items():
            if group_label in data.index:
                value += data.loc[group_label]

        return value

    def find_comp_in_groups(self, component, current_group):
        """"""
        for fkt_group, values in self.group_data.items():
            if fkt_group == current_group:
                continue
            elif component in self.component_data[
                    self.component_data['group'] == fkt_group].index:
                return fkt_group

        msg = 'Target group not found for component ' + component + '.'
        logging.error(msg)
        raise hlp.TESPyNetworkError(msg)

    def print_results(
            self, E_D_min=1000, sort_desc=True,
            busses=True, components=True, connections=True, groups=True,
            network=True):
        r"""Print the results of the exergy analysis to prompt.

        - The results are sorted beginning with the component having the
          biggest exergy destruction by default.
        - Components with an exergy destruction smaller than 1000 W is not
          printed to prompt by default.

        Parameters
        ----------
        E_D_min : float
            Minimum exergy destruction to be printed to prompt.

        sort_des : boolean
            Sort the component results descending by exergy destruction.

        busses : boolean
            Print bus results, default value :code:`True`.

        components : boolean
            Print component results, default value :code:`True`.

        connections : boolean
            Print connection results, default value :code:`True`.

        network : boolean
            Print network results, default value :code:`True`.
        """
        if connections:
            print('##### RESULTS: Connection specific physical exergy and ' +
                  'physical exergy #####')
            print(tabulate(
                self.connection_data, headers='keys',
                tablefmt='psql', floatfmt='.3e'))

        if components:
            df = self.component_data.copy()
            df = df.loc[:, df.columns != 'group']
            if sort_desc:
                df.sort_values(by=['E_D'], ascending=False, inplace=True)

            print('##### RESULTS: Component exergy analysis #####')
            print(tabulate(
                df[df['E_D'] > E_D_min], headers='keys',
                tablefmt='psql', floatfmt='.3e'))

        if busses:
            df = self.bus_data.copy()
            df = df.loc[:, df.columns != 'group']
            if sort_desc:
                df.sort_values(by=['E_D'], ascending=False, inplace=True)

            print('##### RESULTS: Bus exergy analysis #####')
            print(tabulate(
                df[df['E_D'] > E_D_min],
                headers='keys', tablefmt='psql', floatfmt='.3e'))

        if groups:
            df = self.group_overview.copy()
            if sort_desc:
                df.sort_values(by=['E_D'], ascending=False, inplace=True)

            print('##### RESULTS: Bus exergy analysis #####')
            print(tabulate(
                df[df['E_D'] > E_D_min],
                headers='keys', tablefmt='psql', floatfmt='.3e'))

        if network:
            print('##### RESULTS: Network exergy analysis #####')
            print(tabulate(
                self.network_data.to_frame().transpose(),
                headers='keys', tablefmt='psql', floatfmt='.3e', showindex=False))