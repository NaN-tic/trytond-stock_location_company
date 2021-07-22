# This file is part stock_location_company module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest


from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import suite as test_suite


class StockLocationCompanyTestCase(ModuleTestCase):
    'Test Stock Location Company module'
    module = 'stock_location_company'


def suite():
    suite = test_suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            StockLocationCompanyTestCase))
    return suite
