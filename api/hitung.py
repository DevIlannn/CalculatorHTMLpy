import json
import re
from decimal import Context, Decimal, InvalidOperation, localcontext
from http.server import BaseHTTPRequestHandler

PRECISION = 15
MAX_BODY_BYTES = 1024
MAX_OPERAND_LENGTH = 32
OPERAND_PATTERN = re.compile(r'^-?\d+\.?\d*$')

OPERATIONS = {
  '+': lambda a, b: a + b,
  '-': lambda a, b: a - b,
  '*': lambda a, b: a * b,
  '/': lambda a, b: a / b
}


def parseOperand(value):
  if isinstance(value, bool) or not isinstance(value, (int, float, str)):
    raise ValueError('Operand tidak valid')
  text = str(value).strip()
  if len(text) > MAX_OPERAND_LENGTH or not OPERAND_PATTERN.match(text):
    raise ValueError('Operand tidak valid')
  try:
    number = Decimal(text)
  except InvalidOperation:
    raise ValueError('Operand tidak valid')
  if not number.is_finite():
    raise ValueError('Operand tidak valid')
  return number


def formatResult(number):
  text = format(number.normalize(), 'f')
  return '0' if text in ('-0', '') else text


def calculate(a, operator, b):
  if operator not in OPERATIONS:
    raise ValueError('Operator tidak valid')
  if operator == '/' and b == 0:
    raise ValueError('Tidak bisa membagi dengan nol')
  with localcontext(Context(prec=PRECISION)):
    return formatResult(OPERATIONS[operator](a, b))


class handler(BaseHTTPRequestHandler):
  def sendJson(self, status, payload, extraHeaders=None):
    body = json.dumps(payload).encode('utf-8')
    self.send_response(status)
    self.send_header('Content-Type', 'application/json; charset=utf-8')
    self.send_header('Content-Length', str(len(body)))
    self.send_header('Cache-Control', 'no-store')
    for name, value in (extraHeaders or {}).items():
      self.send_header(name, value)
    self.end_headers()
    self.wfile.write(body)

  def do_GET(self):
    self.sendJson(405, {'error': 'Metode tidak diizinkan'}, {'Allow': 'POST'})

  def do_POST(self):
    try:
      length = int(self.headers.get('Content-Length', 0))
    except ValueError:
      length = 0
    if length <= 0 or length > MAX_BODY_BYTES:
      self.sendJson(400, {'error': 'Permintaan tidak valid'})
      return
    try:
      data = json.loads(self.rfile.read(length))
    except ValueError:
      self.sendJson(400, {'error': 'Permintaan tidak valid'})
      return
    if not isinstance(data, dict):
      self.sendJson(400, {'error': 'Permintaan tidak valid'})
      return
    try:
      result = calculate(
        parseOperand(data.get('a')),
        data.get('operator'),
        parseOperand(data.get('b'))
      )
    except ValueError as error:
      self.sendJson(400, {'error': str(error)})
      return
    self.sendJson(200, {'result': result})
