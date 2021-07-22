# This file is part stock_location_company module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import location


def register():
    Pool.register(
        location.Location,
        module='stock_location_company', type_='model')
    Pool.register(
        module='stock_location_company', type_='wizard')
    Pool.register(
        module='stock_location_company', type_='report')
