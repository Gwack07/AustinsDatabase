import sqlite3
from datetime import datetime

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
