import sqlite3
from datetime import datetime
import os

class DatabaseManager:
    def __init__(self, dbName):
        self.dbName = dbName # name of database file
        self.connection = sqlite3.connect(dbName) # creating connection to file
        self.cursor = self.connection.cursor()
        self.connection.execute("PRAGMA foreign_keys = ON")  # enforce referential integrity

        print(f"Connected to {dbName}")

    def convertDataTypes(self, tableName, data): # converts input data into correct data type
        # INTEGER -> int, REAL -> float, TEXT -> str
        columns = self.query(f"PRAGMA table_info({tableName})")
        for col in columns: # interate through columns and isolating name and types
            colName = col[1]
            colType = col[2].upper()
            if colName in data and data[colName] is not None:
                try: # changing data types
                    if colType == "INTEGER":
                        data[colName] = int(data[colName])
                    elif colType == "REAL":
                        data[colName] = float(data[colName])
                    else:
                        data[colName] = str(data[colName])
                except ValueError:
                    raise ValueError(f"{colName} must be of type {colType}")
        return data

    def tableExists(self, tableName): # function to check if table of name already exists
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",(tableName,)) # check if the table exists
        row = self.cursor.fetchone() # fetch the above result
        if row is None: # returns if true or false
            return False
        else:
            return True

    def foreignKeyExists(self, tableName, column, value): # checking if foreeign key exists in specified table
        result = self.query(f"SELECT 1 FROM {tableName} WHERE {column}=?", (value,))
        return bool(result)

    def createTable(self, tableName, columns, replace=False): # create a table in the format at the bottom
        if self.tableExists(tableName):
            if replace: # if it exists and replace is true then replace the table
                self.cursor.execute(f"DROP TABLE IF EXISTS {tableName}")
                print(f"Table '{tableName}' was replaced")
            else:
                print(f"Table '{tableName}' already exists")
                return
        # turns parameters into sql-able format
        columnsList = []
        for col, dtype in columns.items():
            pair = f"{col} {dtype}"
            columnsList.append(pair)
        # join them into one string with commas
        columnsDef = ", ".join(columnsList)

        # execute creating the table
        self.cursor.execute(f"CREATE TABLE {tableName} ({columnsDef})")
        print(f"Table '{tableName}' created")

    def insert(self, tableName, data):
        data = self.convertDataTypes(tableName, data)  # convert inputs first
        self.validateData(tableName, data)  # then validate
        placeholders = ", ".join("?" * len(data))
        columns = ", ".join(data.keys())
        sql = f"INSERT INTO {tableName} ({columns}) VALUES ({placeholders})"
        self.cursor.execute(sql, tuple(data.values()))
        self.connection.commit()
        print(f"Inserted into {tableName}: {data}")

    def isValidDate(self, value: str) -> bool: # check if input is of date format
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except Exception:
            return False

    def validateData(self, tableName, data):
        if tableName == "Suppliers":
            if not data.get("Name") or not data.get("Contact") or not data.get("Address"):
                raise ValueError("Supplier Name, Contact, and Address cannot be empty")

        elif tableName == "Parts":
            if not data.get("Name"):
                raise ValueError("Part name cannot be empty")
            if data.get("StockQTY", 0) < 0:
                raise ValueError("Stock quantity must be >= 0")

        elif tableName == "PartSuppliers":
            if data.get("PurchasePrice", 0) <= 0:
                raise ValueError("PurchasePrice must be > 0")
            if not self.foreignKeyExists("Parts", "PartID", data.get("PartID")):
                raise ValueError("PartID does not exist")
            if not self.foreignKeyExists("Suppliers", "SupplierID", data.get("SupplierID")):
                raise ValueError("SupplierID does not exist")

        elif tableName == "Customers":
            if not data.get("FirstName") or not data.get("LastName") or not data.get("Address"):
                raise ValueError("Customer must have first name, last name, and address")
            if "Email" in data and data["Email"] and "@" not in data["Email"]:
                raise ValueError("Email format invalid")

        elif tableName == "RepairItems":
            if data.get("RepairType") not in ("Car", "Computer"):
                raise ValueError("RepairType must be 'Car' or 'Computer'")
            if not self.foreignKeyExists("Customers", "CustomerID", data.get("CustomerID")):
                raise ValueError("CustomerID does not exist")
            if not data.get("Name"):
                raise ValueError("Repair item must have a name")

        elif tableName == "CarDetails":
            if not self.foreignKeyExists("RepairItems", "ItemID", data.get("ItemID")):
                raise ValueError("ItemID does not exist in RepairItems")
            if not data.get("Make") or not data.get("Model"):
                raise ValueError("Make and Model are required")
            if "Year" in data and (data["Year"] < 1900):
                raise ValueError("Year must be between 1900 and current year")
            if "EngineSize" in data and data["EngineSize"] <= 0:
                raise ValueError("EngineSize must be > 0")

        elif tableName == "ComputerDetails":
            if not self.foreignKeyExists("RepairItems", "ItemID", data.get("ItemID")):
                raise ValueError("ItemID does not exist in RepairItems")
            if not data.get("Brand") or not data.get("CPU"):
                raise ValueError("Brand and CPU are required")
            if "RAM" in data and data["RAM"] < 0:
                raise ValueError("RAM must be >= 0")
            if "Storage" in data and data["Storage"] < 0:
                raise ValueError("Storage must be >= 0")

        elif tableName == "RepairJobs":
            if not self.foreignKeyExists("RepairItems", "ItemID", data.get("RepairItemID")):
                raise ValueError("RepairItemID does not exist")
            if "Price" in data and data["Price"] < 0:
                raise ValueError("Price must be >= 0")

            if data.get("DateReceived") and not self.isValidDate(data["DateReceived"]):
                raise ValueError("DateReceived must be in YYYY-MM-DD format")
            if data.get("DateCompleted") and not self.isValidDate(data["DateCompleted"]):
                raise ValueError("DateCompleted must be in YYYY-MM-DD format")

            if data.get("DateReceived") and data.get("DateCompleted"):
                if data["DateCompleted"] < data["DateReceived"]:
                    raise ValueError("DateCompleted cannot be before DateReceived")

            if "Status" in data and data["Status"] not in ("Pending", "In Progress", "Completed", "Archived"):
                raise ValueError("Status invalid")

        elif tableName == "RepairItemParts":
            if data.get("Quantity", 0) <= 0:
                raise ValueError("Quantity must be > 0")
            if not self.foreignKeyExists("RepairItems", "ItemID", data.get("ItemID")):
                raise ValueError("ItemID does not exist")
            if not self.foreignKeyExists("Parts", "PartID", data.get("PartID")):
                raise ValueError("PartID does not exist")

        elif tableName == "Products":
            if not data.get("Name") or not data.get("Category") or data.get("Price", 0) <= 0:
                raise ValueError("Product must have Name, Category, and Price > 0")
            if data.get("Category") not in ("Laptop", "Desktop", "Other"):
                raise ValueError("Category must be 'Laptop','Desktop', or 'Other'")
            if data.get("Quantity", 0) < 0:
                raise ValueError("Quantity cannot be negative")

        elif tableName == "Sales":
            if not self.foreignKeyExists("Customers", "CustomerID", data.get("CustomerID")):
                raise ValueError("CustomerID does not exist")
            if "SaleAmount" in data and data["SaleAmount"] <= 0:
                raise ValueError("SaleAmount must be > 0")
            if data.get("SaleDate") and not self.isValidDate(data["SaleDate"]):
                raise ValueError("SaleDate must be in YYYY-MM-DD format")

        elif tableName == "SoldItems":
            if not self.foreignKeyExists("Products", "ProductID", data.get("ProductID")):
                raise ValueError("ProductID does not exist")
            if not self.foreignKeyExists("Sales", "SaleID", data.get("SaleID")):
                raise ValueError("SaleID does not exist")
            if data.get("Quantity", 0) <= 0:
                raise ValueError("Quantity must be > 0")
            if data.get("UnitPrice", 0) <= 0:
                raise ValueError("UnitPrice must be > 0")

    def query(self, sql, params=()): # execute a query and return the result
        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def getAllRecords(self, tableName): # return all records from a table
        try:
            return self.query(f"SELECT * FROM {tableName}")
        except Exception as e:
            print(f"Error retrieving records from {tableName}: {e}")
            return []

    def deleteRecord(self, tableName, condition): # delete records with a where condition
        try:
            self.cursor.execute(f"DELETE FROM {tableName} WHERE {condition}")
            self.connection.commit()
            print(f"Record(s) deleted from {tableName} where {condition}")
        except Exception as e:
            print(f"Cannot delete record due to foreign key constraints: {e}")

    def updateRecord(self, tableName, updates, condition): # update record with dict of columns
        setClause = ", ".join([f"{col} = ?" for col in updates])
        try:
            self.cursor.execute(f"UPDATE {tableName} SET {setClause} WHERE {condition}", tuple(updates.values()))
            self.connection.commit()
            print(f"Record(s) updated in {tableName} where {condition}")
        except Exception as e:
            print(f"Cannot update record due to foreign key constraints: {e}")

    def close(self): # close connection to the database
        self.connection.close()
        print("Connection closed")

# how to input data and create tables example
"""
db = DatabaseManager("austinDB.db")

# create students table
db.createTable("students", {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "firstName": "TEXT NOT NULL",
    "lastName": "TEXT NOT NULL",
    "email": "TEXT",
    "enrolledDate": "TEXT"
}, replace=True)

# insert data
db.insert("students", {
    "firstName": "Alice",
    "lastName": "Smith",
    "email": "alice@example.com",
    "enrolledNate": "2025-08-20"
})

# query data
rows = db.query("SELECT * FROM students")
print(rows)

db.close()
"""
def setupDatabase(): # austins database
    # create db manager
    global isEmpty
    isEmpty = True
    if os.path.exists("austinDB.db"):
        os.remove("austinDB.db")

    db = DatabaseManager("austinDB.db")

    # Suppliers
    db.createTable("Suppliers", {
        "SupplierID": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "Name": "TEXT NOT NULL CHECK(Name <> '')",
        "Contact": "TEXT NOT NULL CHECK(Contact <> '')",
        "Address": "TEXT NOT NULL CHECK(Address <> '')",
        "Additional": "TEXT"
    }, replace=True)

    # Parts
    db.createTable("Parts", {
        "PartID": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "Name": "TEXT NOT NULL CHECK(Name <> '')",
        "Description": "TEXT",
        "StockQTY": "INTEGER NOT NULL CHECK(StockQTY >= 0)"
    }, replace=True)

    # PartSuppliers
    db.createTable("PartSuppliers", {
        "PartID": "INTEGER NOT NULL",
        "SupplierID": "INTEGER NOT NULL",
        "PurchasePrice": "REAL NOT NULL CHECK(PurchasePrice > 0)",
        "PRIMARY KEY": "(PartID, SupplierID)",
        "FOREIGN KEY(PartID)": "REFERENCES Parts(PartID)",
        "FOREIGN KEY(SupplierID)": "REFERENCES Suppliers(SupplierID)"
    }, replace=True)

    # Customers
    db.createTable("Customers", {
        "CustomerID": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "FirstName": "TEXT NOT NULL CHECK(FirstName <> '')",
        "LastName": "TEXT NOT NULL CHECK(LastName <> '')",
        "Email": "TEXT CHECK(Email LIKE '_%@_%._%')",
        "Phone": "TEXT",
        "Address": "TEXT NOT NULL CHECK(Address <> '')"
    }, replace=True)

    # RepairItems
    db.createTable("RepairItems", {
        "ItemID": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "RepairType": "TEXT NOT NULL CHECK(RepairType IN ('Car','Computer'))",
        "CustomerID": "INTEGER NOT NULL",
        "Name": "TEXT NOT NULL CHECK(Name <> '')",
        "Description": "TEXT",
        "FOREIGN KEY(CustomerID)": "REFERENCES Customers(CustomerID)"
    }, replace=True)

    # CarDetails (subtype of RepairItems)
    db.createTable("CarDetails", {
        "ItemID": "INTEGER PRIMARY KEY",
        "Make": "TEXT NOT NULL",
        "Model": "TEXT NOT NULL",
        "Year": "INTEGER CHECK(Year >= 1900)",
        "EngineSize": "REAL CHECK(EngineSize > 0)",
        "Additional": "TEXT",
        "FOREIGN KEY(ItemID)": "REFERENCES RepairItems(ItemID)"
    }, replace=True)

    # ComputerDetails (subtype of RepairItems)
    db.createTable("ComputerDetails", {
        "ItemID": "INTEGER PRIMARY KEY",
        "Brand": "TEXT NOT NULL",
        "RAM": "INTEGER CHECK(RAM >= 0)",
        "Storage": "INTEGER CHECK(Storage >= 0)",
        "CPU": "TEXT NOT NULL",
        "FOREIGN KEY(ItemID)": "REFERENCES RepairItems(ItemID)"
    }, replace=True)

    # RepairJobs
    db.createTable("RepairJobs", {
        "RepairID": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "JobType": "TEXT NOT NULL",
        "DateReceived": "DATE NOT NULL CHECK(DateReceived <= CURRENT_DATE)",
        "DateCompleted": "DATE CHECK(DateCompleted >= DateReceived)",
        "Status": "TEXT CHECK(Status IN ('Pending','In Progress','Completed','Archived'))",
        "Price": "REAL CHECK(Price >= 0)",
        "RepairItemID": "INTEGER NOT NULL",
        "FOREIGN KEY(RepairItemID)": "REFERENCES RepairItems(ItemID)"
    }, replace=True)

    # RepairItemParts

    db.createTable("RepairItemParts", {
        "ItemID": "INTEGER NOT NULL",
        "PartID": "INTEGER NOT NULL",
        "Quantity": "INTEGER NOT NULL CHECK(Quantity > 0)",
        "PRIMARY KEY": "(ItemID, PartID)",
        "FOREIGN KEY(ItemID)": "REFERENCES RepairItems(ItemID)",
        "FOREIGN KEY(PartID)": "REFERENCES Parts(PartID)"
    }, replace=True)

    # Products
    db.createTable("Products", {
        "ProductID": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "Category": "TEXT NOT NULL CHECK(Category IN ('Laptop','Desktop','Other'))",
        "Quantity": "INTEGER NOT NULL CHECK(Quantity >= 0)",
        "Name": "TEXT NOT NULL",
        "Description": "TEXT",
        "Price": "REAL NOT NULL CHECK(Price > 0)"
    }, replace=True)

    # Sales
    db.createTable("Sales", {
        "SaleID": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "SaleDate": "DATE NOT NULL CHECK(SaleDate <= CURRENT_DATE)",
        "SaleAmount": "REAL NOT NULL CHECK(SaleAmount > 0)",
        "CustomerID": "INTEGER NOT NULL",
        "FOREIGN KEY(CustomerID)": "REFERENCES Customers(CustomerID)"
    }, replace=True)

    # SoldItems
    db.createTable("SoldItems", {
        "SaleItemID": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "ProductID": "INTEGER NOT NULL",
        "SaleID": "INTEGER NOT NULL",
        "Quantity": "INTEGER NOT NULL CHECK(Quantity > 0)",
        "UnitPrice": "REAL NOT NULL CHECK(UnitPrice > 0)",
        "FOREIGN KEY(ProductID)": "REFERENCES Products(ProductID)",
        "FOREIGN KEY(SaleID)": "REFERENCES Sales(SaleID)"
    }, replace=True)
    db.close()

def populateDatabase(): # inserting data - must execute after database created, deletes whole database
    db = DatabaseManager("austinDB.db")
    global isEmpty
    isEmpty = False

 # Suppliers
    suppliers = [
        ("PLE Computers", "sales@ple.com.au", "Perth WA", "Local store"),
        ("Amazon", "support@amazon.com", "Online", "Fast delivery"),
        ("MSY Technology", "contact@msy.com.au", "Osborne Park WA", ""),
        ("Scorptec", "info@scorptec.com.au", "Melbourne VIC", "Great range"),
        ("Umart", "sales@umart.com.au", "Brisbane QLD", ""),
        ("eBay", "support@ebay.com", "Online", "Second-hand parts"),
        ("Harvey Norman", "sales@harveynorman.com.au", "Perth WA", ""),
        ("JB Hi-Fi", "info@jbhifi.com.au", "Sydney NSW", ""),
        ("Officeworks", "sales@officeworks.com.au", "Perth WA", ""),
        ("Tech Warehouse", "info@techwarehouse.com", "Online", "Wholesale")
    ]
    for s in suppliers:
        db.insert("Suppliers", {
            "Name": s[0], "Contact": s[1], "Address": s[2], "Additional": s[3]
        })

    # Parts
    parts = [
        ("Intel i5 CPU", "10th Gen Intel i5 processor", 5),
        ("NVIDIA GTX 1660", "6GB graphics card", 2),
        ("AMD Ryzen 5 5600X", "6-core CPU", 4),
        ("16GB DDR4 RAM", "Corsair Vengeance LPX", 10),
        ("500GB SSD", "Samsung 970 EVO", 8),
        ("1TB HDD", "Western Digital Blue", 12),
        ("750W PSU", "EVGA 80+ Gold", 6),
        ("ATX Case", "NZXT H510", 3),
        ("Intel i7 CPU", "12th Gen Intel i7 processor", 2),
        ("NVIDIA RTX 3060", "12GB graphics card", 1)
    ]
    for p in parts:
        db.insert("Parts", {"Name": p[0], "Description": p[1], "StockQTY": p[2]})

    # PartSuppliers
    mappings = [
        (1, 1, 250.00),
        (2, 2, 400.00),
        (3, 3, 320.00),
        (4, 4, 120.00),
        (5, 5, 90.00),
        (6, 2, 50.00),
        (7, 6, 110.00),
        (8, 7, 95.00),
        (9, 1, 450.00),
        (10, 3, 600.00)
    ]
    for m in mappings:
        db.insert("PartSuppliers", {
            "PartID": m[0], "SupplierID": m[1], "PurchasePrice": m[2]
        })

    # Customers
    customers = [
        ("Alice", "Smith", "alice@example.com", "0400123456", "123 Main St, Perth"),
        ("Bob", "Johnson", "bob@example.com", "0400654321", "456 High St, Perth"),
        ("Charlie", "Brown", "charlie@example.com", "0400333444", "789 King St, Perth"),
        ("Daisy", "Miller", "daisy@example.com", "0400777888", "22 Queen St, Perth"),
        ("Ethan", "Clark", "ethan@example.com", "0400555666", "88 River Rd, Perth"),
        ("Fiona", "Lopez", "fiona@example.com", "0400999000", "11 Hill St, Perth"),
        ("George", "Wilson", "george@example.com", "0400111222", "55 Ocean Dr, Perth"),
        ("Hannah", "Moore", "hannah@example.com", "0400222333", "77 Park Ave, Perth"),
        ("Ian", "Taylor", "ian@example.com", "0400444555", "99 Forest Rd, Perth"),
        ("Julia", "Anderson", "julia@example.com", "0400888999", "12 Sunset Blvd, Perth")
    ]
    for c in customers:
        db.insert("Customers", {
            "FirstName": c[0], "LastName": c[1], "Email": c[2], "Phone": c[3], "Address": c[4]
        })

    # RepairItems
    repair_items = [
        ("Computer", 1, "Gaming PC", "Custom build"),
        ("Car", 2, "Toyota Corolla", "2008 sedan"),
        ("Computer", 3, "Office Laptop", "Dell Inspiron"),
        ("Car", 4, "Mazda 3", "2012 hatchback"),
        ("Computer", 5, "Workstation", "HP EliteDesk"),
        ("Car", 6, "Honda Civic", "2010 model"),
        ("Computer", 7, "Server PC", "Rackmount build"),
        ("Car", 8, "Ford Focus", "2015 model"),
        ("Computer", 9, "MacBook Pro", "2019 13-inch"),
        ("Car", 10, "Holden Commodore", "2005 sedan")
    ]
    for r in repair_items:
        db.insert("RepairItems", {
            "RepairType": r[0], "CustomerID": r[1], "Name": r[2], "Description": r[3]
        })

    # Products
    products = [
        ("Desktop", 3, "Refurbished Gaming PC", "Ryzen 5 + GTX 1660 build", 750.00),
        ("Laptop", 5, "Refurbished Dell Laptop", "i5 + 8GB RAM", 450.00),
        ("Desktop", 2, "Workstation Build", "Xeon + 32GB RAM", 950.00),
        ("Laptop", 1, "MacBook Pro 2019", "13-inch Retina", 1100.00),
        ("Desktop", 4, "Budget PC", "Pentium + 4GB RAM", 300.00),
        ("Laptop", 2, "HP EliteBook", "14-inch business laptop", 600.00),
        ("Desktop", 1, "Gaming Beast", "i7 + RTX 3060", 1500.00),
        ("Other", 6, "Used Monitor", "24-inch FHD", 120.00),
        ("Other", 8, "Keyboard + Mouse Bundle", "Logitech combo", 80.00),
        ("Desktop", 2, "Linux Workstation", "Ryzen 7 + 16GB RAM", 900.00)
    ]
    for p in products:
        db.insert("Products", {
            "Category": p[0], "Quantity": p[1], "Name": p[2], "Description": p[3], "Price": p[4]
        })

    # Sales
    sales = [
        ("2025-08-01", 750.00, 1),
        ("2025-08-02", 450.00, 2),
        ("2025-08-03", 950.00, 3),
        ("2025-08-04", 1100.00, 4),
        ("2025-08-05", 300.00, 5),
        ("2025-08-06", 600.00, 6),
        ("2025-08-07", 1500.00, 7),
        ("2025-08-08", 120.00, 8),
        ("2025-08-09", 80.00, 9),
        ("2025-08-10", 900.00, 10)
    ]
    for s in sales:
        db.insert("Sales", {"SaleDate": s[0], "SaleAmount": s[1], "CustomerID": s[2]})

    # SoldItems
    soldItems = [
        (1, 1, 1, 750.00),
        (2, 2, 1, 450.00),
        (3, 3, 1, 950.00),
        (4, 4, 1, 1100.00),
        (5, 5, 1, 300.00),
        (6, 6, 1, 600.00),
        (7, 7, 1, 1500.00),
        (8, 8, 1, 120.00),
        (9, 9, 1, 80.00),
        (10, 10, 1, 900.00)
    ]
    for si in soldItems:
        db.insert("SoldItems", {
            "ProductID": si[0], "SaleID": si[1], "Quantity": si[2], "UnitPrice": si[3]
        })

    computerDetails = [
        ("Custom Build", 16, 512, "Intel i5-10400"),
        ("Dell", 8, 256, "Intel i5-8250U"),
        ("HP", 32, 1000, "Intel Xeon E5-1650 v3"),
        ("Supermicro", 64, 2000, "Intel Xeon Silver 4110"),
        ("Apple", 16, 512, "Intel i5-8279U")
    ]
    comp_ids = [r[0] for r in db.query("SELECT ItemID FROM RepairItems WHERE RepairType='Computer' ORDER BY ItemID")]
    for item_id, d in zip(comp_ids, computerDetails):
        db.insert("ComputerDetails", {
            "ItemID": item_id, "Brand": d[0], "RAM": d[1], "Storage": d[2], "CPU": d[3]
        })

    # CarDetails
    carDetails = [
        ("Toyota", "Corolla", 2008, 1.8, "White, automatic"),
        ("Mazda", "3", 2012, 2.0, "Hatchback"),
        ("Honda", "Civic", 2010, 1.8, "Blue, new plugs"),
        ("Ford", "Focus", 2015, 2.0, "Needs brake pads"),
        ("Holden", "Commodore", 2005, 3.6, "Rear suspension noise")
    ]

    carIds = [r[0] for r in db.query("SELECT ItemID FROM RepairItems WHERE RepairType='Car' ORDER BY ItemID")]
    for itemId, d in zip(carIds, carDetails):
        db.insert("CarDetails", {
            "ItemID": itemId, "Make": d[0], "Model": d[1], "Year": d[2],
            "EngineSize": d[3], "Additional": d[4]
        })


    # RepairJobs
    repairJobs = [
        ("Hardware Repair", "2025-08-01", "2025-08-05", "Completed", 150.00, 1),
        ("Engine Overhaul", "2025-08-10", None, "In Progress", 800.00, 2),
        ("Screen Replacement", "2025-08-03", "2025-08-04", "Completed", 200.00, 3),
        ("Brake Service", "2025-08-06", "2025-08-07", "Completed", 300.00, 4),
        ("Power Supply Fix", "2025-08-08", None, "Pending", 120.00, 5),
        ("Engine Diagnostics", "2025-08-09", None, "In Progress", 250.00, 6),
        ("Motherboard Replacement", "2025-08-11", None, "Pending", 400.00, 7),
        ("Transmission Repair", "2025-08-12", None, "In Progress", 1000.00, 8),
        ("Keyboard Repair", "2025-08-13", "2025-08-14", "Completed", 80.00, 9),
        ("Suspension Fix", "2025-08-15", None, "Pending", 600.00, 10)
    ]
    for r in repairJobs:
        db.insert("RepairJobs", {
            "JobType": r[0],
            "DateReceived": r[1],
            "DateCompleted": r[2],
            "Status": r[3],
            "Price": r[4],
            "RepairItemID": r[5]
        })

    # RepairItemParts
    repairItemParts = [
        (1, 1, 1),
        (1, 2, 1),
        (3, 4, 1),
        (5, 7, 1),
        (7, 9, 1),
        (9, 5, 1),
        (2, 6, 2),
        (4, 8, 1),
        (6, 10, 1),
        (10, 3, 1)
    ]
    for rip in repairItemParts:
        db.insert("RepairItemParts", {
            "ItemID": rip[0],
            "PartID": rip[1],
            "Quantity": rip[2]
        })

    db.close()
    print("Database populated with 10 dummy entries per table")


def displayRecords(db, tableName): #displays all columns in a table with headers
    try:
        rows = db.query(f"SELECT * FROM {tableName}")
        if rows:
            columns = []
            for desc in db.cursor.description:
                columns.append(desc[0])
            print("\n" + " | ".join(columns)) # header
            print("-" * 50)

            for r in rows: # print out each record

                rowValues = []
                for value in r:
                    if value is None:
                        rowValues.append("")  # replace None with empty string
                    else:
                        rowValues.append(str(value))  # make sure it’s a string

                print(" | ".join(rowValues))
        else:
            print(f"No records in {tableName}.")
    except Exception as e:
        print(f"Error: {e}")

def getInputForTable(db, tableName): # getting input for new/updated records
    columns = db.query(f"PRAGMA table_info({tableName})")  # sql function to return column info
    '''cid, name, type, notnull, dflt_value, pk''' # return result syntax

    data = {}
    for col in columns:
        name = col[1]
        required = col[3] == 1  # NOT NULL

        if col[5]:  # primary key autoincrement - no user input for pk
            continue

        if required: # required/ not
            prompt = f'{name} (Required): '
        else:
            prompt = f'{name} (Optional): '

        value = input(prompt).strip() #removing unnesscary

        if value == "/": #cancelling function
            print("Cancelled. Returning to menu.")
            return None

        if required and not value:
            print(f"{name} is required")
            return None

        if value:
            data[name] = value
    return data

def chooseTable(): # promting user to enter table - returns tablenumber of choice
    while True:
        choice = input("Choose table number ('/' to cancel): ").strip()
        if choice == "/":
            return None
        if not choice.isdigit():
            print("Please enter a valid number.")
            continue
        index = int(choice)
        if 1 <= index <= len(tableList):
            return index - 1
        else:
            print(f"Please enter a number between 1 and {len(tableList)}.")

def addRecord(db): # function to add a table
    displayTables(db)
    tableChoice = chooseTable()
    if tableChoice is None:
        return
    tableName = tableList[tableChoice] # tableList global var

    # Special case for cardetails - has user definef pk
    if tableName.lower() == "cardetails":
        try:
            itemId = int(input("Enter the ItemID from RepairItems (Required): "))
            data = {
                "ItemID": itemId,
                "Make": input("Make (Required): "),
                "Model": input("Model (Required): "),
                "Year": input("Year (Optional): "),
                "EngineSize": input("EngineSize (Optional): "),
                "Additional": input("Additional (Optional): ")
            }
            db.insert("CarDetails", data)
        except Exception as e:
            print(f"Error inserting: {e}")
        return

    # Special case for computerdetails like above
    if tableName.lower() == "computerdetails":
        try:
            itemId = int(input("Enter the ItemID from RepairItems (Required): "))
            data = {
                "ItemID": itemId,
                "Brand": input("Brand (Required): "),
                "RAM": input("RAM (Optional): "),
                "Storage": input("Storage (Optional): "),
                "CPU": input("CPU (Required): ")
            }
            db.insert("ComputerDetails", data)
        except Exception as e:
            print(f"Error inserting: {e}")
        return

    # generic case for all other tables
    data = getInputForTable(db, tableName)
    if data:
        try:
            db.insert(tableName, data)
        except Exception as e:
            print(f"Error inserting: {e}")

def updateRecord(db): # function to update record of specified table
    displayTables(db)
    tableChoice = chooseTable()
    if tableChoice is None:
        return
    tableName = tableList[tableChoice]

    condition = input("Enter condition for record to update (e.g., ItemID=1): ").strip() # condition like used to find record
    if condition == "/":
        print("Cancelled. Returning to menu.")
        return

    columns = db.query(f"PRAGMA table_info({tableName})")
    updates = {}
    for col in columns:
        name = col[1]
        if col[5]:  # skip primary key
            continue
        required = col[3] == 1
        if required:
            prompt = f"New value for {name} (Required): "
        else:
            prompt = f"New value for {name} (Optional): "

        value = input(prompt).strip()
        if value == "/":
            print("Cancelled. Returning to menu.")
            return
        if value:
            updates[name] = value

    if updates:
        try:
            db.updateRecord(tableName, updates, condition)
        except Exception as e:
            print(f"Error updating: {e}")

def deleteRecord(db): # function to delete records with parameters
    displayTables(db)
    tableChoice = chooseTable()
    if tableChoice is None:
        return
    tableName = tableList[tableChoice]

    condition = input("Enter condition for record to delete (e.g., ItemID=1): ").strip()
    if condition == "/":
        print("Cancelled. Returning to menu.")
        return

    db.deleteRecord(tableName, condition)

def customQuery(db): # function to execute custom query
    query = input("Enter your SQL query ('/' to cancel): ").strip()
    if query == "/":
        print("Cancelled. Returning to menu.")
        return
    displayQueryResults(db, query)

def miscQueries(db): # function containing possible queries that can be enumerated - add more in future
    queries = [
        ("List all suppliers sorted alphabetically by name",
         "SELECT * FROM Suppliers ORDER BY Name ASC"),
        ("Find all customers whose last name starts with 'S'",
         "SELECT * FROM Customers WHERE LastName LIKE 'S%'"),
        ("Show the top five most expensive products in stock",
         "SELECT * FROM Products ORDER BY Price DESC LIMIT 5"),
        ("Get all repair jobs that are not complete",
         "SELECT * FROM RepairJobs WHERE Status != 'Completed'"),
        ("List all computer repairs in the last week",
         "SELECT * FROM RepairItems r JOIN RepairJobs j ON r.ItemID=j.RepairItemID WHERE r.RepairType='Computer' AND j.DateReceived >= date('now','-7 days')"),
        ("List all parts with their supplier name",
         "SELECT p.Name AS PartName, s.Name AS SupplierName FROM Parts p JOIN PartSuppliers ps ON p.PartID=ps.PartID JOIN Suppliers s ON ps.SupplierID=s.SupplierID"),
        ("Get all repair jobs with customer name and repair item description",
         "SELECT j.RepairID, c.FirstName, c.LastName, r.Name AS ItemName, r.Description FROM RepairJobs j JOIN RepairItems r ON j.RepairItemID=r.ItemID JOIN Customers c ON r.CustomerID=c.CustomerID"),
        ("Show all products sold with sale date and customer name",
         "SELECT si.SaleItemID, p.Name AS ProductName, s.SaleDate, c.FirstName, c.LastName FROM SoldItems si JOIN Products p ON si.ProductID=p.ProductID JOIN Sales s ON si.SaleID=s.SaleID JOIN Customers c ON s.CustomerID=c.CustomerID"),
        ("Find all cars repaired, showing make, model, repair job status",
         "SELECT r.Name AS CarName, c.Make, c.Model, j.Status FROM CarDetails c JOIN RepairItems r ON c.ItemID=r.ItemID JOIN RepairJobs j ON r.ItemID=j.RepairItemID"),
        ("Count how many repair jobs each customer has had",
         "SELECT c.FirstName, c.LastName, COUNT(j.RepairID) AS JobCount FROM Customers c LEFT JOIN RepairItems r ON c.CustomerID=r.CustomerID LEFT JOIN RepairJobs j ON r.ItemID=j.RepairItemID GROUP BY c.CustomerID"),
        ("Calculate the total quantity of each part used in all repairs",
         "SELECT p.Name, SUM(rip.Quantity) AS TotalUsed FROM Parts p JOIN RepairItemParts rip ON p.PartID=rip.PartID GROUP BY p.PartID"),
        ("Find the total sales revenue from selling items",
         "SELECT SUM(UnitPrice * Quantity) AS TotalRevenue FROM SoldItems"),
        ("List customers who have spent more than $100",
         "SELECT c.FirstName, c.LastName, SUM(s.SaleAmount) AS TotalSpent FROM Customers c JOIN Sales s ON c.CustomerID=s.CustomerID GROUP BY c.CustomerID HAVING TotalSpent > 100"),
        ("Get the average price of a computer repair",
         "SELECT AVG(j.Price) AS AvgComputerRepair FROM RepairJobs j JOIN RepairItems r ON j.RepairItemID=r.ItemID WHERE r.RepairType='Computer'"),
        ("Show all tables in the database",
         "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"),
        ("Check the total number of records in each table",
         """SELECT 'Suppliers', COUNT(*) FROM Suppliers UNION ALL
            SELECT 'Parts', COUNT(*) FROM Parts UNION ALL
            SELECT 'Customers', COUNT(*) FROM Customers UNION ALL
            SELECT 'RepairItems', COUNT(*) FROM RepairItems UNION ALL
            SELECT 'RepairJobs', COUNT(*) FROM RepairJobs UNION ALL
            SELECT 'RepairItemParts', COUNT(*) FROM RepairItemParts UNION ALL
            SELECT 'Products', COUNT(*) FROM Products UNION ALL
            SELECT 'Sales', COUNT(*) FROM Sales UNION ALL
            SELECT 'SoldItems', COUNT(*) FROM SoldItems""")
    ]

    print("\n--- Misc Queries ---")
    for i, q in enumerate(queries, 1): # printing the list of queries
        print(f"{i}. {q[0]}")

    choice = input("Choose query number ('/' to cancel): ").strip()
    if choice == "/":
        print("Cancelled. Returning to menu.")
        return
    if not choice.isdigit() or not (1 <= int(choice) <= len(queries)): # checking choice is valid
        print("Invalid choice.")
        return

    displayQueryResults(db, queries[int(choice)-1][1])

def saveResultsToFile(columns, rows, filename="results.txt"): # function to save query results to file
    try:
        with open(filename, "w", encoding="utf-8") as f:
            # Write header
            f.write(" | ".join(columns) + "\n")
            f.write("-" * 50 + "\n")

            # Write each row
            for r in rows:
                row_values = []
                for i in r:
                    if i is None:
                        row_values.append("")
                    else:
                        row_values.append(str(i))
                f.write(" | ".join(row_values) + "\n")

        print(f"Results successfully written to {filename}")
    except Exception as e:
        print(f"Error writing to file: {e}")


def displayQueryResults(db, query):
    try:
        db.cursor.execute(query)
        rows = db.cursor.fetchall()
        if rows:
            columns = [desc[0] for desc in db.cursor.description]

            # Print results as usual
            print("\n" + " | ".join(columns))
            print("-" * 50)
            for r in rows:
                text = []
                for i in r:
                    if i is None:
                        text.append("")
                    else:
                        text.append(str(i))
                print(" | ".join(text))

            # Ask if user wants to save
            save = input("Save results to file? (y/n): ").strip().lower()
            if save == "y":
                filename = input("Enter filename (default: results.txt): ").strip()
                if not filename:
                    filename = "results.txt"
                saveResultsToFile(columns, rows, filename)

        else:
            print("No results.")

    except Exception as e:
        print(f"Error: {e}")


def displayTables(db): # fetch and display all tables in the database
    global tableList
    rows = db.query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;") # function to return tables
    tableList = []
    for row in rows:
        tableList.append(row[0])

    print("\n--- Tables ---")
    for i, t in enumerate(tableList, 1): # Showing list of tables
        print(f"{i}. {t}")

def main(): # mainline
    db = DatabaseManager("austinDB.db")
    while True: # constantly display choices
        print("\n--- Austin's Database Console ('/' to cancel) ---")
        print("1. View Records")
        print("2. Add Record")
        print("3. Update Record")
        print("4. Delete Record")
        print("5. Custom Query")
        print("6. Miscellaneous Queries")
        print("7. Setup Database")
        print("8. Populate Database (must be empty)")
        print("9. Exit")

        choice = input("Select an option: ").strip()
        if choice == "/":
            continue

        if choice == "1": # logic to process choices and execute various functions
            displayTables(db)
            tableChoice = chooseTable()
            if tableChoice is not None:
                displayRecords(db, tableList[tableChoice])
        elif choice == "2":
            addRecord(db)
        elif choice == "3":
            updateRecord(db)
        elif choice == "4":
            deleteRecord(db)
        elif choice == "5":
            customQuery(db)
        elif choice == "6":
            miscQueries(db)
        elif choice == "7":
            setupDatabase()
        elif choice == "8":
            if isEmpty:
                populateDatabase()
            else:
                print('Database already populated.')
        elif choice == "9":
            db.close()
            break
        else:
            print("Invalid option. Try again.")



main()
