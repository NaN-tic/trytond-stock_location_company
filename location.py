from trytond.pool import PoolMeta
from trytond.model import fields
from trytond.transaction import Transaction
from trytond.pyson import Eval
from trytond.i18n import gettext
from trytond.exceptions import UserError
from trytond.pyson import If, Eval


class Location(metaclass=PoolMeta):
    __name__ = 'stock.location'

    company = fields.Many2One('company.company', 'Company',
        domain=[
            ('id', If(Eval('context', {}).contains('company'), '=', '!='),
                Eval('context', {}).get('company', -1)),
            ])

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.parent.domain = [('company', '=', Eval('company'))]
        cls.parent.depends = ['company']

    @classmethod
    def default_company(cls):
        return Transaction().context.get('company') or None

    @classmethod
    def validate(cls, locations):
        super().validate(locations)
        for location in locations:
            location.check_company()

    def check_company(self):
        if (self.company is not None and
                self.company.id != Transaction().context.get('company')):
            raise UserError(gettext(
                    'stock_location_company.msg_wrong_company',
                    location=self.rec_name))
        for child in self.childs:
            if child.company != self.company:
                raise UserError(gettext(
                    'stock_location_company.msg_wrong_company',
                    location=self.rec_name))
