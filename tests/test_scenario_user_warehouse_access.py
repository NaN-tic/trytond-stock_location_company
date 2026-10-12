import unittest

from proteus import Model
from trytond.model.exceptions import AccessError
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules, set_user


class TestUserWarehouseAccess(unittest.TestCase):
    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):
        config = activate_modules('stock_location_company')
        create_company()
        company = get_company()
        Company = Model.get('company.company')
        Party = Model.get('party.party')
        User = Model.get('res.user')
        Location = Model.get('stock.location')
        party = Party(name='Other Company')
        party.save()
        other_company = Company(party=party, currency=company.currency)
        other_company.save()
        admin_id = config.user
        context = {'company': company.id}
        User.write([admin_id], {
                'companies': [('add', [other_company.id])],
                'company_filter': 'all',
                }, context)

        other_context = {'company': other_company.id}
        storage_id, = Location.create([{
                    'name': 'Other Storage',
                    'type': 'storage',
                    'company': other_company.id,
                    }], other_context)
        warehouse_id, = Location.create([{
                    'name': 'Other Warehouse',
                    'type': 'warehouse',
                    'company': other_company.id,
                    'input_location': storage_id,
                    'output_location': storage_id,
                    'storage_location': storage_id,
                    }], other_context)
        user_id, empty_id = User.create([{
                    'name': 'Other User',
                    'login': 'other',
                    'companies': [('add', [other_company.id])],
                    'company': other_company.id,
                    'warehouse': warehouse_id,
                    }, {
                    'name': 'User Without Warehouse',
                    'login': 'empty',
                    'companies': [('add', [company.id])],
                    'company': company.id,
                    'warehouse': None,
                    }], context)

        # The name is visible through user administration even when the
        # administrator's company filter hides the assigned warehouse.
        User.write([admin_id], {'company_filter': 'one'}, context)
        rows = User.read([user_id, empty_id],
            ['name', 'warehouse', 'warehouse.rec_name'], context)
        rows = {r['id']: r for r in rows}
        self.assertEqual(rows[user_id]['warehouse'], warehouse_id)
        self.assertEqual(rows[user_id]['warehouse.'], {
                'id': warehouse_id, 'rec_name': 'Other Warehouse'})
        self.assertIsNone(rows[empty_id]['warehouse'])
        self.assertIsNone(rows[empty_id]['warehouse.'])
        row, = User.read([user_id], ['warehouse.rec_name'], context)
        self.assertNotIn('warehouse', row)
        self.assertEqual(row['warehouse.']['rec_name'], 'Other Warehouse')

        # Saving an unrelated preference preserves the warehouse assignment.
        User.write([user_id], {'name': 'Renamed User'}, context)
        row, = User.read([user_id], ['name', 'warehouse'], context)
        self.assertEqual(row['name'], 'Renamed User')
        self.assertEqual(row['warehouse'], warehouse_id)

        # The exception grants neither location access nor other related data.
        with self.assertRaises(AccessError):
            Location.read([warehouse_id], ['rec_name'], context)
        self.assertEqual(Location.search([('id', '=', warehouse_id)],
                0, None, None, context), [])
        with self.assertRaises(AccessError):
            User.read([user_id],
                ['warehouse.rec_name', 'warehouse.company'], context)
        with self.assertRaises(AccessError):
            Location.write([warehouse_id], {'name': 'Forbidden'}, context)

        # A client-supplied warehouse for the current user is not an assignment.
        with self.assertRaises(AccessError):
            User.read([admin_id], ['warehouse.rec_name'],
                dict(context, warehouse=warehouse_id))

        # An ordinary user may read user records, but cannot use the exception.
        set_user(empty_id)
        with self.assertRaises(AccessError):
            User.read([user_id], ['warehouse.rec_name'], context)

        # The administrative display also works without membership in the
        # warehouse's company, and with the all-companies filter enabled.
        set_user(admin_id)
        User.write([admin_id], {
                'companies': [('remove', [other_company.id])],
                'company_filter': 'all',
                }, context)
        row, = User.read([user_id], ['warehouse.rec_name'], context)
        self.assertEqual(row['warehouse.']['rec_name'], 'Other Warehouse')
        with self.assertRaises(AccessError):
            Location.read([warehouse_id], ['rec_name'], context)
