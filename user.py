# This file is part sale_shop module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.pyson import Eval


class User(metaclass=PoolMeta):
    __name__ = "res.user"

    @classmethod
    def __setup__(cls):
        super(User, cls).__setup__()
        cls.warehouse.domain += [('company', '=', Eval('company', -1))]
        cls.warehouse.depends.add('company')

    @fields.depends('warehouse')
    def on_change_company(self):
        Location = Pool().get('stock.location')

        super().on_change_company()
        self.warehouse = None

        if self.company:
            with Transaction().set_context(company=self.company.id, _check_access=False):
                warehouses = Location.search([
                    ('type', '=', 'warehouse'),
                    ('company', '=', self.company),
                    ])
                if len(warehouses) == 1:
                    self.warehouse = warehouses[0]
