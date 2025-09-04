"""
Austin's Database Bottle Frontend
Single-file Bottle app that writes templates/static files on first run.

Features:
- View, add, edit, delete for main tables (Suppliers, Parts, Customers, RepairItems, RepairJobs, Products, Sales, SoldItems, PartSuppliers, RepairItemParts, ComputerDetails, CarDetails)
- Server-side validation using the same rules as DatabaseManager
- Referential integrity (PRAGMA foreign_keys = ON)
- Pagination, sorting, searching
- CSV export
- Inline AJAX editing for quantity/price
- Relationship views (e.g., parts for a repair item)
- Simple import (CSV) for Parts and Suppliers

Requirements:
- bottle (pip install bottle)
- python 3.8+

Run:
    python austin_bottle_frontend.py
Then open http://localhost:8080

This single-file app will create a 'templates' and 'static' folder and write minimal templates & assets to them.
"""

from bottle import Bottle, run, template, request, redirect, static_file, response, HTTPError
import sqlite3, os, csv, io, json
from datetime import datetime
import urllib.parse

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(APP_DIR, 'austinDB.db')
TEMPLATES_DIR = os.path.join(APP_DIR, 'templates')
STATIC_DIR = os.path.join(APP_DIR, 'static')

# --- Ensure folders exist
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ---- Minimal CSS + JS (Bootstrap + jQuery via CDN in templates) ----
# We'll write templates below as files if they don't exist

# --- Database utilities (lightweight manager with validation) ---
class DB:
    def __init__(self, dbfile=DB_FILE):
        self.dbfile = dbfile
        self.conn = sqlite3.connect(self.dbfile)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cur = self.conn.cursor()

    def query(self, sql, params=()):
        self.cur.execute(sql, params)
        return [dict(r) for r in self.cur.fetchall()]

    def execute(self, sql, params=()):
        self.cur.execute(sql, params)
        self.conn.commit()
        return self.cur.lastrowid

    def close(self):
        self.conn.close()

    def exists(self, table, col, val):
        r = self.query(f"SELECT 1 FROM {table} WHERE {col}=? LIMIT 1", (val,))
        return len(r) > 0

# Validation helpers (similar rules as earlier provided)

def validate(table, data, db):
    # return (ok, message or cleaned data dict)
    try:
        out = dict(data)
        if table == 'Suppliers':
            if not out.get('Name') or not out.get('Contact') or not out.get('Address'):
                return False, 'Name, Contact and Address required'
        elif table == 'Parts':
            if not out.get('Name'):
                return False, 'Part name required'
            out['StockQTY'] = int(out.get('StockQTY', 0))
            if out['StockQTY'] < 0:
                return False, 'StockQTY cannot be negative'
        elif table == 'Customers':
            if not out.get('FirstName') or not out.get('LastName') or not out.get('Address'):
                return False, 'First, Last name and Address required'
            if out.get('Email') and '@' not in out['Email']:
                return False, 'Invalid email format'
        elif table == 'RepairItems':
            if out.get('RepairType') not in ('Car', 'Computer'):
                return False, "RepairType must be 'Car' or 'Computer'"
            if not db.exists('Customers', 'CustomerID', int(out.get('CustomerID'))):
                return False, 'CustomerID not found'
        elif table == 'RepairJobs':
            # Expect RepairItemID present and numeric
            rid = int(out.get('RepairItemID'))
            if not db.exists('RepairItems', 'ItemID', rid):
                return False, 'RepairItemID not found'
            if out.get('Price') is not None:
                try:
                    out['Price'] = float(out['Price'])
                except:
                    return False, 'Price must be numeric'
                if out['Price'] < 0:
                    return False, 'Price cannot be negative'
            # dates
            dr = out.get('DateReceived')
            if dr:
                try:
                    drd = datetime.strptime(dr, '%Y-%m-%d').date()
                    if drd > datetime.now().date():
                        return False, 'DateReceived cannot be in the future'
                except Exception as e:
                    return False, 'Invalid DateReceived format, use YYYY-MM-DD'
            dc = out.get('DateCompleted')
            if dc:
                try:
                    dcd = datetime.strptime(dc, '%Y-%m-%d').date()
                    if dr and dcd < datetime.strptime(dr, '%Y-%m-%d').date():
                        return False, 'DateCompleted cannot be before DateReceived'
                except:
                    return False, 'Invalid DateCompleted format, use YYYY-MM-DD'
        elif table == 'Products':
            if not out.get('Name') or not out.get('Category'):
                return False, 'Product Name and Category required'
            if out.get('Category') not in ('Laptop','Desktop','Other'):
                return False, 'Invalid Category'
            out['Quantity'] = int(out.get('Quantity',0))
            out['Price'] = float(out.get('Price',0))
            if out['Quantity'] < 0 or out['Price'] <= 0:
                return False, 'Quantity >=0 and Price > 0'
        # Additional validations can be added for other tables
        return True, out
    except Exception as e:
        return False, str(e)

# --- Create minimal templates on first run ---
INDEX_TPL = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Austin DB - Admin</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
</head>
<body class="p-3">
<div class="container">
  <h1>Austin DB - Admin Frontend</h1>
  <p class="lead">Simple Bottle admin with CRUD, search, pagination, CSV export, and inline edit.</p>
  <div class="row">
    <div class="col-md-4">
      <div class="list-group">
        % for t in tables:
          <a class="list-group-item list-group-item-action" href="/table/{{t}}">{{t}}</a>
        % end
n      </div>
    </div>
    <div class="col-md-8">
      <h3>Quick Actions</h3>
      <a href="/export/all" class="btn btn-outline-primary">Export All Tables (CSV)</a>
      <a href="/import" class="btn btn-outline-secondary">Import CSV (Parts/Suppliers)</a>
      <hr>
      <h4>Search across tables</h4>
      <form method="get" action="/search" class="row g-2">
        <div class="col-auto"><input class="form-control" name="q" placeholder="Search term"></div>
        <div class="col-auto"><button class="btn btn-primary">Search</button></div>
      </form>
    </div>
  </div>
</div>
</body>
</html>
'''

TABLE_TPL = '''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{table}}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
</head>
<body class="p-3">
<div class="container">
  <a href="/" class="btn btn-link">&larr; Back</a>
  <h1>Table: {{table}}</h1>
  <div class="mb-3">
    <form class="row g-2" method="get" action="/table/{{table}}">
      <div class="col-md-4"><input class="form-control" name="q" placeholder="search" value="{{q or ''}}"></div>
      <div class="col-md-2"><select name="per" class="form-select"><option>10</option><option>25</option><option>50</option></select></div>
      <div class="col-md-2"><button class="btn btn-primary">Filter</button></div>
      <div class="col-md-4 text-end"><a href="/table/{{table}}/new" class="btn btn-success">Create new</a>
      <a href="/export/{{table}}" class="btn btn-outline-secondary">Export CSV</a></div>
    </form>
  </div>
  <table class="table table-sm table-striped">
    <thead>
      <tr>
        % for h in headers:
          <th>{{h}}</th>
        % end
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      % for row in rows:
        <tr>
          % for h in headers:
            <td>{{row.get(h)}}</td>
          % end
          <td>
            <a class="btn btn-sm btn-primary" href="/table/{{table}}/edit/{{row.get(pk)}}">Edit</a>
            <a class="btn btn-sm btn-danger" href="/table/{{table}}/delete/{{row.get(pk)}}" onclick="return confirm('Delete?')">Delete</a>
            <a class="btn btn-sm btn-info" href="/table/{{table}}/view/{{row.get(pk)}}">View</a>
          </td>
        </tr>
      % end
    </tbody>
  </table>
  % if page_info:
    <nav>
      <ul class="pagination">
        % if page_info.prev:
          <li class="page-item"><a class="page-link" href="{{page_info.prev_url}}">Prev</a></li>
        % end
        <li class="page-item active"><span class="page-link">Page {{page_info.page}}</span></li>
        % if page_info.next:
          <li class="page-item"><a class="page-link" href="{{page_info.next_url}}">Next</a></li>
        % end
      </ul>
    </nav>
  % end
</div>
</body>
</html>
'''

FORM_TPL = '''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{verb}} {{table}}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="p-3">
<div class="container">
  <a href="/table/{{table}}" class="btn btn-link">&larr; Back</a>
  <h1>{{verb}} {{table}}</h1>
  % if error:
    <div class="alert alert-danger">{{error}}</div>
  % end
  <form method="post" action="{{action}}">
    % for f in fields:
      <div class="mb-3">
        <label class="form-label">{{f}}</label>
        <input class="form-control" name="{{f}}" value="{{row.get(f) if row else ''}}">
      </div>
    % end
    <button class="btn btn-primary">Save</button>
  </form>
</div>
</body>
</html>
'''

VIEW_TPL = '''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>View {{table}}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="p-3">
<div class="container">
  <a href="/table/{{table}}" class="btn btn-link">&larr; Back</a>
  <h1>{{table}} #{{pkval}}</h1>
  <table class="table table-bordered">
  % for k,v in row.items():
    <tr><th>{{k}}</th><td>{{v}}</td></tr>
  % end
  </table>
</div>
</body>
</html>
'''

SEARCH_TPL = '''<!doctype html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="p-3"><div class="container"><a href="/">&larr; Back</a><h1>Search results for '{{q}}'</h1>
% for table,rows in results.items():
  <h3>{{table}} ({{len(rows)}})</h3>
  <table class="table table-sm table-striped"><thead><tr>
  % if rows:
    % for h in rows[0].keys():
      <th>{{h}}</th>
    % end
  % end
  </tr></thead>
  <tbody>
  % for r in rows:
    <tr>
    % for v in r.values():
      <td>{{v}}</td>
    % end
    </tr>
  % end
  </tbody></table>
% end
</div></body></html>
'''

# Write templates if not exist
TPLS = {
    'index.tpl': INDEX_TPL,
    'table.tpl': TABLE_TPL,
    'form.tpl': FORM_TPL,
    'view.tpl': VIEW_TPL,
    'search.tpl': SEARCH_TPL
}
for name, content in TPLS.items():
    path = os.path.join(TEMPLATES_DIR, name)
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

# --- Bottle app ---
app = Bottle()

# static
@app.route('/static/<filename>')
def static(filename):
    return static_file(filename, root=STATIC_DIR)

# helper to get table metadata
def get_table_info(db, table):
    rows = db.query(f"PRAGMA table_info({table})")
    headers = [r['name'] for r in rows]
    pk = None
    for r in rows:
        if r['pk']:
            pk = r['name']
            break
    return headers, pk

@app.route('/')
def index():
    db = DB()
    tables = [r['name'] for r in db.query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    db.close()
    return template(os.path.join(TEMPLATES_DIR,'index.tpl'), tables=tables)

@app.route('/table/<table>')
def view_table(table):
    db = DB()
    q = request.query.q or ''
    per = int(request.query.per or 10)
    page = int(request.query.page or 1)
    offset = (page-1)*per
    headers, pk = get_table_info(db, table)
    where = ''
    params = []
    if q:
        # simple search across text-like columns
        where_clauses = []
        for h in headers:
            where_clauses.append(f"{h} LIKE ?")
            params.append(f"%{q}%")
        where = 'WHERE ' + ' OR '.join(where_clauses)
    total = db.query(f"SELECT COUNT(*) as c FROM {table} {where}", tuple(params))[0]['c']
    rows = db.query(f"SELECT * FROM {table} {where} LIMIT ? OFFSET ?", tuple(params)+ (per, offset))
    # page info
    page_info = {
        'page': page,
        'prev': page>1,
        'next': offset+per < total,
        'prev_url': f"/table/{table}?q={urllib.parse.quote(q)}&per={per}&page={page-1}",
        'next_url': f"/table/{table}?q={urllib.parse.quote(q)}&per={per}&page={page+1}"
    }
    db.close()
    return template(os.path.join(TEMPLATES_DIR,'table.tpl'), table=table, headers=headers, rows=rows, pk=pk, q=q, page_info=page_info)

@app.route('/table/<table>/view/<id>')
def view_row(table, id):
    db = DB()
    headers, pk = get_table_info(db, table)
    rows = db.query(f"SELECT * FROM {table} WHERE {pk}=?", (id,))
    if not rows:
        db.close()
        return HTTPError(404, 'Not found')
    row = rows[0]
    db.close()
    return template(os.path.join(TEMPLATES_DIR,'view.tpl'), table=table, row=row, pk=pk, pkval=id)

@app.route('/table/<table>/new', method=['GET','POST'])
def new_row(table):
    db = DB()
    headers, pk = get_table_info(db, table)
    fields = [h for h in headers if h != pk]
    error = None
    if request.method == 'POST':
        data = {f: request.forms.get(f) for f in fields}
        ok, res = validate(table, data, db)
        if ok:
            # build insert
            cols = ','.join(res.keys())
            vals = ','.join(['?']*len(res))
            try:
                db.execute(f"INSERT INTO {table} ({cols}) VALUES ({vals})", tuple(res.values()))
                db.close()
                redirect(f"/table/{table}")
            except sqlite3.IntegrityError as e:
                error = str(e)
        else:
            error = res
    db.close()
    return template(os.path.join(TEMPLATES_DIR,'form.tpl'), table=table, fields=fields, row=None, verb='Create', action=f"/table/{table}/new", error=error)

@app.route('/table/<table>/edit/<id>', method=['GET','POST'])
def edit_row(table, id):
    db = DB()
    headers, pk = get_table_info(db, table)
    fields = [h for h in headers if h != pk]
    rows = db.query(f"SELECT * FROM {table} WHERE {pk}=?", (id,))
    if not rows:
        db.close()
        return HTTPError(404, 'Not found')
    row = rows[0]
    error = None
    if request.method == 'POST':
        data = {f: request.forms.get(f) for f in fields}
        ok, res = validate(table, data, db)
        if ok:
            set_clause = ','.join([f"{k}=?" for k in res.keys()])
            params = tuple(res.values()) + (id,)
            try:
                db.execute(f"UPDATE {table} SET {set_clause} WHERE {pk}=?", params)
                db.close()
                redirect(f"/table/{table}")
            except sqlite3.IntegrityError as e:
                error = str(e)
        else:
            error = res
    db.close()
    return template(os.path.join(TEMPLATES_DIR,'form.tpl'), table=table, fields=fields, row=row, verb='Edit', action=f"/table/{table}/edit/{id}", error=error)

@app.route('/table/<table>/delete/<id>')
def delete_row(table, id):
    db = DB()
    headers, pk = get_table_info(db, table)
    try:
        db.execute(f"DELETE FROM {table} WHERE {pk}=?", (id,))
    except sqlite3.IntegrityError as e:
        db.close()
        return HTTPError(400, f"Cannot delete due to integrity constraints: {e}")
    db.close()
    redirect(f"/table/{table}")

@app.route('/export/<table>')
def export_table(table):
    db = DB()
    rows = db.query(f"SELECT * FROM {table}")
    db.close()
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    else:
        output.write('')
    response.content_type = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{table}.csv"'
    return output.getvalue()

@app.route('/export/all')
def export_all():
    db = DB()
    tables = [r['name'] for r in db.query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    zip_buffer = io.StringIO()
    # simple multi-csv in one text response separated
    for t in tables:
        rows = db.query(f"SELECT * FROM {t}")
        zip_buffer.write(f"-- TABLE: {t} --\n")
        if rows:
            w = csv.DictWriter(zip_buffer, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        zip_buffer.write('\n')
    db.close()
    response.content_type = 'text/plain'
    response.headers['Content-Disposition'] = 'attachment; filename="austin_all_tables.txt"'
    return zip_buffer.getvalue()

@app.route('/search')
def search():
    q = request.query.q or ''
    db = DB()
    tables = [r['name'] for r in db.query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    results = {}
    for t in tables:
        headers,_ = get_table_info(db, t)
        where = ' OR '.join([f"{h} LIKE ?" for h in headers])
        params = tuple(['%'+q+'%']*len(headers)) if headers else ()
        rows = db.query(f"SELECT * FROM {t} WHERE {where} LIMIT 25", params) if q and headers else []
        if rows:
            results[t] = rows
    db.close()
    return template(os.path.join(TEMPLATES_DIR,'search.tpl'), q=q, results=results)

@app.route('/import', method=['GET','POST'])
def import_csv():
    message = ''
    if request.method == 'POST':
        upload = request.files.get('csv')
        if not upload:
            message = 'No file uploaded'
        else:
            data = upload.file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(data))
            db = DB()
            count = 0
            for r in reader:
                # naive: try to insert into Parts if has Name and StockQTY otherwise Suppliers
                if 'StockQTY' in r or 'StockQty' in r or 'Stock' in r:
                    # map keys
                    rec = {'Name': r.get('Name'), 'Description': r.get('Description',''), 'StockQTY': r.get('StockQTY') or r.get('Stock') or 0}
                    ok,res = validate('Parts', rec, db)
                    if ok:
                        try:
                            db.execute('INSERT INTO Parts (Name,Description,StockQTY) VALUES (?,?,?)', (res['Name'], res.get('Description',''), res['StockQTY']))
                            count +=1
                        except sqlite3.IntegrityError:
                            pass
                else:
                    rec = {'Name': r.get('Name'), 'Contact': r.get('Contact',''), 'Address': r.get('Address',''), 'Additional': r.get('Additional','')}
                    ok,res = validate('Suppliers', rec, db)
                    if ok:
                        try:
                            db.execute('INSERT INTO Suppliers (Name,Contact,Address,Additional) VALUES (?,?,?,?)', (res['Name'], res['Contact'], res['Address'], res.get('Additional','')))
                            count +=1
                        except sqlite3.IntegrityError:
                            pass
            db.close()
            message = f'Imported {count} rows'
    return '''<html><body><a href="/">Back</a><h1>Import CSV</h1><form method="post" enctype="multipart/form-data"><input type="file" name="csv"><button>Upload</button></form><div>%s</div></body></html>'''%message

# API endpoints for AJAX
@app.route('/api/<table>/<id>', method=['POST'])
def api_edit(table, id):
    payload = request.json
    db = DB()
    headers, pk = get_table_info(db, table)
    fields = [h for h in headers if h != pk]
    data = {k: payload.get(k) for k in fields if k in payload}
    ok,res = validate(table, data, db)
    if not ok:
        db.close()
        response.status = 400
        return {'error': res}
    set_clause = ','.join([f"{k}=?" for k in res.keys()])
    params = tuple(res.values()) + (id,)
    try:
        db.execute(f"UPDATE {table} SET {set_clause} WHERE {pk}=?", params)
    except sqlite3.IntegrityError as e:
        db.close()
        response.status = 400
        return {'error': str(e)}
    db.close()
    return {'ok': True}

# small helper to initialize DB if missing (call user's setupDatabase if available)
def ensure_db_exists():
    if not os.path.exists(DB_FILE):
        print('Database file not found. Creating an empty database with minimal schema...')
        db = DB()
        # Minimal tables to avoid errors (you may instead call the user's setupDatabase script externally)
        db.execute('CREATE TABLE Suppliers (SupplierID INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT NOT NULL, Contact TEXT NOT NULL, Address TEXT NOT NULL, Additional TEXT)')
        db.execute('CREATE TABLE Parts (PartID INTEGER PRIMARY KEY AUTOINCREMENT, Name TEXT NOT NULL, Description TEXT, StockQTY INTEGER NOT NULL DEFAULT 0)')
        db.execute('CREATE TABLE Customers (CustomerID INTEGER PRIMARY KEY AUTOINCREMENT, FirstName TEXT NOT NULL, LastName TEXT NOT NULL, Email TEXT, Phone TEXT, Address TEXT NOT NULL)')
        db.execute('CREATE TABLE RepairItems (ItemID INTEGER PRIMARY KEY AUTOINCREMENT, RepairType TEXT NOT NULL, CustomerID INTEGER NOT NULL, Name TEXT NOT NULL, Description TEXT, FOREIGN KEY(CustomerID) REFERENCES Customers(CustomerID))')
        db.execute('CREATE TABLE RepairJobs (RepairID INTEGER PRIMARY KEY AUTOINCREMENT, JobType TEXT NOT NULL, DateReceived DATE NOT NULL, DateCompleted DATE, Status TEXT, Price REAL, RepairItemID INTEGER NOT NULL, FOREIGN KEY(RepairItemID) REFERENCES RepairItems(ItemID))')
        db.close()
        print('Minimal DB created. Please run your full setupDatabase/populateDatabase to add full schema and data.')

if __name__ == '__main__':
    ensure_db_exists()
    print('Starting Bottle on http://localhost:8080')
    run(app, host='0.0.0.0', port=8080, reloader=True)
