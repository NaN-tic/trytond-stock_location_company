
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.modules.company.tests import CompanyTestMixin, create_company
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.transaction import Transaction


class StockLocationCompanyTestCase(CompanyTestMixin, ModuleTestCase):
    'Test StockLocationCompany module'
    module = 'stock_location_company'

    @with_transaction()
    def test_user_company(self):
        'Test user company'
        pool = Pool()
        User = pool.get('res.user')
        Location = pool.get('stock.location')

        transaction = Transaction()

        warehouse, = Location.search([('type', '=', 'warehouse')], limit=1)
        warehouse2, = Location.copy([warehouse])

        company1 = create_company()
        company2 = create_company('Michael Scott Paper Company',
            currency=company1.currency)
        company2.save()

        user1, user2 = User.create([{
                    'name': 'Jim Halper',
                    'login': 'jim',
                    'companies': [('add', [company1.id, company2.id])],
                    'company': company1.id,
                    }, {
                    'name': 'Pam Beesly',
                    'login': 'pam',
                    'companies': [('add', [company2.id])],
                    'company': company2.id,
                    }])
        self.assertTrue(user1)

        with transaction.set_user(user1.id):
            user1, user2 = User.browse([user1.id, user2.id])
            self.assertEqual(user1.company, company1)
            self.assertEqual(user2.company, company2)

            # create warehouse from company1
            with transaction.set_context({'company': company1.id, 'companies': [company1.id]}):
                storage = Location(
                    name='Warehouse',
                    type='storage',
                    code='STO2',
                    )
                storage.save()
                warehouse = Location(
                    name='Warehouse',
                    code='WH%s' % company1.id,
                    type='warehouse',
                    company=company1,
                    input_location=storage,
                    output_location=storage,
                    storage_location=storage)
                warehouse.save()

            # create warehouse from company2
            with transaction.set_context({'company': company2.id, 'companies': [company2.id]}):
                storage2 = Location(
                    name='Warehouse',
                    type='storage',
                    code='STO2',
                    )
                storage2.save()
                warehouse2 = Location(
                    name='Warehouse',
                    code='WH%s' % company2.id,
                    type='warehouse',
                    company=company2,
                    input_location=storage2,
                    output_location=storage2,
                    storage_location=storage2)
                warehouse2.save()

            with transaction.set_context({'company': company1.id, 'companies': [company1.id, company2.id]}):
                warehouse, = Location.search([
                    ('type', '=', 'warehouse'),
                    ('company', '=', company1),
                    ], limit=1)
                user1.warehouse = warehouse
                user1.save()

                # when on_change_company, set new warehouse from the company
                user1.company = company2
                user1.on_change_company()
                self.assertEqual(user1.warehouse.company, user1.company)

del ModuleTestCase
