from sanic import Blueprint
from .ipfs import ipfs
from .heartbeat import heartbeat
from .cdms import cdms
from .tables import tables
from .columns import columns

api_v1 = Blueprint.group(
  ipfs,
  cdms,
  heartbeat,
  tables,
  columns,
  url_prefix='/v1'
)