from tespy.networks import Network
from tespy.components import (Source, Sink, Turbine, Compressor, Valve)
from tespy.connections import Connection, Bus
from tespy.tools import ExergyAnalysis
from tespy.tools.helpers import get_chem_ex_lib
chemexlib = get_chem_ex_lib("Ahrendts")

# network
nw = Network(T_unit="C", p_unit="bar", h_unit="kJ / kg")

# components
turb = Turbine("Turbine")
valv = Valve("Valve")
so = Source("Source")
si = Sink("Sink")

# Connections
so_2_turb = Connection(so, 'out1', turb, 'in1', label="Inlet")
turb_2_valv = Connection(turb, 'out1', valv, 'in1', label="Turbine-Valve")
valv_2_si = Connection(valv, 'out1', si, 'in1', label="Outlet")

nw.add_conns(so_2_turb,
                     turb_2_valv, valv_2_si)

# define parameters
turb.set_attr(eta_s=0.8)
valv.set_attr(pr=0.5)
so_2_turb.set_attr(fluid={'Water': 1}, T=600, p=100,  m=20)
turb_2_valv.set_attr(T=30)

# solve
nw.solve(mode='design')
nw.print_results()


""" +++ exergy analysis +++ """
# define ambient
pamb = 1
Tamb = 15

# define busses
power = Bus('power output')
power.add_comps(
    {'comp': turb, 'char': 0.6, 'base': 'component'})

hot_steam = Bus('fresh steam dif')
hot_steam.add_comps(
    {'comp': so, 'base': 'bus'},
    {'comp': si})

#valv.serving_components = [turb]
exe_eco_input = {'Source_c': 10, 'Turbine_Z': 50, 'Valve_Z': 10}
ean = ExergyAnalysis(nw, E_P=[power], E_F=[hot_steam], E_L=[], internal_busses=[])
ean.analyse(pamb=pamb, Tamb=Tamb, Chem_Ex=chemexlib)
ean.evaluate_exergoeconomics(Tamb=Tamb, Exe_Eco_Costs=exe_eco_input)
ean.print_results(Exe_Eco_An=True)
