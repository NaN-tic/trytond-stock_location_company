# This file is part stock_location_company module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelSQL, Unique, fields
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
        self.warehouse = self.get_company_warehouse()

        if self.company and not self.warehouse:
            with Transaction().set_context(company=self.company.id, _check_access=False):
                warehouses = Location.search([
                    ('type', '=', 'warehouse'),
                    ('company', '=', self.company),
                    ])
                if len(warehouses) == 1:
                    self.warehouse = warehouses[0]

    @classmethod
    def _get_preferences(cls, user, context_only=False):
        preferences = super()._get_preferences(user,
            context_only=context_only)
        warehouse = user.get_company_warehouse()
        if warehouse:
            preferences['warehouse'] = warehouse.id
        else:
            preferences.pop('warehouse', None)
        return preferences

    @classmethod
    def write(cls, users, values, *args):
        Location = Pool().get('stock.location')
        write_args = []
        actions = iter((users, values) + args)
        for users, values in zip(actions, actions):
            if 'company' in values and 'warehouse' not in values:
                for user in users:
                    values = values.copy()
                    warehouse = user.get_company_warehouse(
                        values['company'])
                    if not warehouse and values['company']:
                        with Transaction().set_context(
                                company=values['company'],
                                _check_access=False):
                            warehouses = Location.search([
                                    ('type', '=', 'warehouse'),
                                    ('company', '=', values['company']),
                                    ])
                            if len(warehouses) == 1:
                                warehouse = warehouses[0]
                    values['warehouse'] = warehouse.id if warehouse else None
                    write_args.extend(([user], values))
            else:
                write_args.extend((users, values))

        if not write_args:
            # if 'company' and 'warehouse' are specified, but there are no
            # users, write_args may be empty
            return
        super().write(*write_args)
        actions = iter(write_args)
        for users, values in zip(actions, actions):
            if 'warehouse' not in values:
                continue
            for user in users:
                user.set_company_warehouse(
                    values['warehouse'], values.get('company'))

    def get_company_warehouse(self, company=None):
        company = company or self.company
        if not self.id or not company:
            return None
        company_id = company.id if hasattr(company, 'id') else company
        UserWarehouse = Pool().get('res.user-stock.location.company')
        warehouses = UserWarehouse.search([
                ('user', '=', self.id),
                ('company', '=', company_id),
                ], limit=1)
        if warehouses:
            return warehouses[0].warehouse
        warehouse = self.warehouse
        if warehouse and warehouse.company.id == company_id:
            return warehouse

    def set_company_warehouse(self, warehouse, company=None):
        company = company or self.company
        if not company:
            return
        company_id = company.id if hasattr(company, 'id') else company
        UserWarehouse = Pool().get('res.user-stock.location.company')
        records = UserWarehouse.search([
                ('user', '=', self.id),
                ('company', '=', company_id),
                ], limit=1)
        if records and warehouse:
            UserWarehouse.write(records, {'warehouse': warehouse})
        elif warehouse:
            UserWarehouse.create([{
                    'user': self.id,
                    'company': company_id,
                    'warehouse': warehouse,
                    }])
        elif records:
            UserWarehouse.delete(records)


class UserWarehouse(ModelSQL):
    'User - Company - Warehouse'
    __name__ = 'res.user-stock.location.company'

    user = fields.Many2One('res.user', 'User', ondelete='CASCADE', required=True)
    company = fields.Many2One(
        'company.company', 'Company', ondelete='CASCADE', required=True)
    warehouse = fields.Many2One(
        'stock.location', 'Warehouse', ondelete='CASCADE', required=True,
        domain=[
            ('type', '=', 'warehouse'),
            ('company', '=', Eval('company', -1)),
            ])

    @classmethod
    def __setup__(cls):
        super().__setup__()
        table = cls.__table__()
        cls._sql_constraints += [
            ('user_company_uniq', Unique(table, table.user, table.company),
                'stock_location_company.msg_user_company_warehouse_unique'),
            ]
