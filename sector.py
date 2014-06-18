#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, PYSONEncoder
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateTransition, StateAction

__all__ = ['Sector', 'PartySector', 'Party', 'ProductSector', 'Product',
    'OpenSector']
__metaclass__ = PoolMeta

STATES = {
    'readonly': Eval('active', False),
}
DEPENDS = ['active']

SEPARATOR = ' / '


class Sector(ModelSQL, ModelView):
    'Sector'
    __name__ = 'party.sector'
    name = fields.Char('Name', required=True, states=STATES, translate=True,
        depends=DEPENDS)
    parent = fields.Many2One('party.sector', 'Parent',
        select=True, states=STATES, depends=DEPENDS)
    childs = fields.One2Many('party.sector', 'parent',
       'Children', states=STATES, depends=DEPENDS)
    active = fields.Boolean('Active')

    @classmethod
    def __setup__(cls):
        super(Sector, cls).__setup__()
        cls._sql_constraints = [
            ('name_parent_uniq', 'UNIQUE(name, parent)',
                'The name of a party sector must be unique by parent.'),
            ]
        cls._error_messages.update({
                'wrong_name': ('Invalid sector name "%%s": You can not use '
                    '"%s" in name field.' % SEPARATOR),
                })
        cls._order.insert(1, ('name', 'ASC'))

    @staticmethod
    def default_active():
        return True

    @classmethod
    def validate(cls, sectors):
        super(Sector, cls).validate(sectors)
        cls.check_recursion(sectors, rec_name='name')
        for sector in sectors:
            sector.check_name()

    def check_name(self):
        if SEPARATOR in self.name:
            self.raise_user_error('wrong_name', (self.name,))

    def get_rec_name(self, name):
        if self.parent:
            return self.parent.get_rec_name(name) + SEPARATOR + self.name
        return self.name

    @classmethod
    def search_rec_name(cls, name, clause):
        if isinstance(clause[2], basestring):
            values = clause[2].split(SEPARATOR)
            values.reverse()
            domain = []
            field = 'name'
            for name in values:
                domain.append((field, clause[1], name))
                field = 'parent.' + field
            sectors = cls.search(domain, order=[])
            return [('id', 'in', [sector.id for sector in sectors])]
        #TODO Handle list
        return [('name',) + tuple(clause[1:])]


class SectorRelatedMixin:
    related_sectors = fields.Function(fields.Many2Many('party.sector', None,
            None, 'Sectors'),
        'get_related_sectors', setter='set_related_sectors')

    def get_related_sectors(self, name):
        pool = Pool()
        Sector = pool.get('party.sector')
        if not self.sectors:
            return []
        sectors = Sector.search([('parent', 'child_of', [x.id for x in
                        self.sectors])])
        return [s.id for s in sectors]

    @classmethod
    def set_related_sectors(cls, records, name, value):
        cls.write(records, {
                'sectors': value,
                })


class PartySector(ModelSQL):
    'Party - Sector'
    __name__ = 'party.party-party.sector'

    party = fields.Many2One('party.party', 'Party', select=True, required=True,
        ondelete='CASCADE')
    sector = fields.Many2One('party.sector', 'Sector', select=True,
        required=True, ondelete='CASCADE')


class Party(SectorRelatedMixin):
    __name__ = 'party.party'

    sectors = fields.Many2Many('party.party-party.sector', 'party', 'sector',
        'Sectors')
    products = fields.Function(fields.Many2Many('product.product', None, None,
            'products'),
        'get_products', searcher='search_products')

    def get_products(self, name):
        pool = Pool()
        Product = pool.get('product.product')
        products = Product.search([
                ('sectors', 'child_of', [x.id for x in self.sectors],
                    'parent'),
                ])
        return [x.id for x in products]

    @classmethod
    def search_products(cls, name, clause):
        pool = Pool()
        Product = pool.get('product.product')
        products = Product.search([tuple(('id',)) + tuple(clause[1:])])
        sectors = set()
        for product in products:
            for sector in product.sectors:
                sectors.add(sector.id)
        return [('sectors', 'in', list(sectors))]


class ProductSector(ModelSQL):
    'Product - Sector'
    __name__ = 'product.product-party.sector'

    product = fields.Many2One('product.product', 'Product', select=True,
        required=True, ondelete='CASCADE')
    sector = fields.Many2One('party.sector', 'Sector', select=True,
        required=True, ondelete='CASCADE')


class Product(SectorRelatedMixin):
    __name__ = 'product.product'

    sectors = fields.Many2Many('product.product-party.sector', 'product',
        'sector', 'Sectors')
    parties = fields.Function(fields.Many2Many('party.party', None, None,
            'Parties'),
        'get_parties', searcher='search_parties')

    def get_parties(self, name):
        pool = Pool()
        Party = pool.get('party.party')
        parties = Party.search([
                ('sectors', 'child_of', [x.id for x in self.sectors],
                    'parent'),
                ])
        return [x.id for x in parties]

    @classmethod
    def search_parties(cls, name, clause):
        pool = Pool()
        Party = pool.get('party.party')
        parties = Party.search([tuple(('id',)) + tuple(clause[1:])])
        sectors = set()
        for party in parties:
            for sector in party.sectors:
                sectors.add(sector.id)
        return [('sectors', 'in', list(sectors))]


class OpenSector(Wizard):
    'Open Sector Wizard'
    __name__ = 'party.sector.open'
    start = StateTransition()
    party = StateAction('party_sector.act_related_party')
    product = StateAction('party_sector.act_related_product')

    def transition_start(self):
        return Transaction().context.get('sector_related_action', 'end')

    def prepare_action(self, action):
        active_id = Transaction().context.get('active_id')
        action['pyson_domain'] = PYSONEncoder().encode(
            [('sectors', 'child_of', [active_id], 'parent')])
        return action, {}

    do_party = prepare_action
    do_product = prepare_action
