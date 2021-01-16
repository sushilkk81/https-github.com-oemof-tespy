# -*- coding: utf-8

"""Module for global variables used by other modules of the tespy package.

This file is part of project TESPy (github.com/oemof/tespy). It's copyrighted
by the contributors recorded in the version control history of the file,
available from its original location tespy/tools/global_vars.py

SPDX-License-Identifier: MIT
"""

err = 1e-6
molar_masses = {}
gas_constants = {}
gas_constants['uni'] = 8.3144598
# Define colors for highlighting values in result table
coloring = {
    'end': '\033[0m',
    'set': '\033[94m',
    'err': '\033[31m',
    'var': '\033[32m'
}

fluid_property_data = {
    'm': {
        'text': 'mass flow',
        'SI_unit': 'kg / s',
        'units': {'kg / s': 1, 'kg / min': 60, 'kg / h': 3600, 't / h': 3.6}
    },
    'v': {
        'text': 'volumetric flow',
        'SI_unit': 'm3 / s',
        'units': {
            'm3 / s': 1, 'm3 / min': 1 / 60, 'm3 / h': 1 / 3.6e3,
            'l / s': 1 / 1e3, 'l / min': 1 / 60e3, 'l / h': 1 / 3.6e6
        }
    }, 'p': {
        'text': 'pressure',
        'SI_unit': 'Pa',
        'units': {
            'Pa': 1, 'kPa': 1e3, 'psi': 6.8948e3,
            'bar': 1e5, 'atm': 1.01325e5, 'MPa': 1e6
        }
    },
    'h': {
        'text': 'enthalpy',
        'SI_unit': 'J / kg',
        'units': {
            'J / kg': 1, 'kJ / kg': 1e3, 'MJ / kg': 1e6,
            'cal / kg': 1 / 4.184, 'kcal / kg': 1e3 / 4.184,
            'Wh / kg': 1 / 3.6e3, 'kWh / kg': 1 / 3.6e6
        }
    },
    'T': {
        'text': 'temperature',
        'SI_unit': 'K',
        'units': {
            'K': [0, 1], 'R': [0, 5 / 9],
            'C': [273.15, 1], 'F': [459.67, 5 / 9]
        }
    },
    'vol': {
        'text': 'specific volume',
        'SI_unit': 'm3 / kg',
        'units': {'m3 / kg': 1, 'l / kg': 1e-3}
    },
    'x': {
        'text': 'vapor mass fraction',
        'SI_unit': '-',
        'units': {'-': 1, '%': 1e-2, 'ppm': 1e-6}
    },
    's': {
        'text': 'entropy',
        'SI_unit': 'J / kgK',
        'units': {'J / kgK': 1, 'kJ / kgK': 1e3, 'MJ / kgK': 1e6}
    }
}
