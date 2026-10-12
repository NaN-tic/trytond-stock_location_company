# This file is part stock_location_company module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelSQL, Unique, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction, without_check_access
from trytond.pyson import Eval


class User(metaclass=PoolMeta):
    __name__ = "res.user"

    @classmethod
    def __setup__(cls):
        super(User, cls).__setup__()
        cls.warehouse.domain += [('company', '=', Eval('company', -1))]
        cls.warehouse.depends.add('company')

    @classmethod
    def read(cls, ids, fields_names):
        pool = Pool()
        ModelAccess = pool.get('ir.model.access')
        Location = pool.get('stock.location')
        transaction = Transaction()
        if (not fields_names or 'warehouse.rec_name' not in fields_names
                or not transaction.check_access
                or not ModelAccess.check(
                    cls.__name__, 'write', raise_exception=False)):
            return super().read(ids, fields_names)

        # Read the users with normal access checks before resolving just the
        # display name of their assigned warehouse across company boundaries.
        names = [n for n in fields_names if n != 'warehouse.rec_name']
        if 'warehouse' not in names:
            names.append('warehouse')
        result = super().read(ids, names)
        warehouse_ids = {r['warehouse'] for r in result if r['warehouse']}
        context_ids = {
            r['warehouse'] for r in result
            if r['id'] == transaction.user and r['warehouse']
            and transaction.context.get('warehouse')}
        # stock.User.read may replace the current user's warehouse with a
        # client-supplied context value. Such a value must pass normal checks.
        warehouses = Location.read(list(context_ids), ['rec_name'])
        with without_check_access():
            warehouses += Location.read(
                list(warehouse_ids - context_ids), ['rec_name'])
        warehouses = {w['id']: w for w in warehouses}
        for row in result:
            warehouse = row['warehouse']
            if warehouse:
                row.setdefault('warehouse.', {}).update(warehouses[warehouse])
            else:
                row['warehouse.'] = None
            if 'warehouse' not in fields_names:
                del row['warehouse']
        return result

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
