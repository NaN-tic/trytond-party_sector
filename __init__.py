# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .sector import *


def register():
    Pool.register(
        Sector,
        PartySector,
        Party,
        ProductSector,
        Product,
        module='party_sector', type_='model')
    Pool.register(
        OpenSector,
        module='party_sector', type_='wizard')
