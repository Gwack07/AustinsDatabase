from databaseManager import DatabaseManager
import os

def setupDatabase(): # austins database
    # create db manager
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

    # PartSuppliers (many-to-many)
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
        "Year": "INTEGER CHECK(Year BETWEEN 1900 AND strftime('%Y','now'))",
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

    # RepairItemParts (many-to-many)

    db.createTable("RepairItemParts", {
        "ItemID": "INTEGER NOT NULL",
        "PartID": "INTEGER NOT NULL",
        "Quantity": "INTEGER NOT NULL CHECK(Quantity > 0)",
        "PRIMARY KEY": "(ItemID, PartID)",
        "FOREIGN KEY(ItemID)": "REFERENCES RepairItems(ItemID)",
        "FOREIGN KEY(PartID)": "REFERENCES Parts(PartID)"
    }, replace=True)

    db.createTable("CarDetails", {
        "ItemID": "INTEGER PRIMARY KEY",
        "Make": "TEXT NOT NULL",
        "Model": "TEXT NOT NULL",
        "Year": "INTEGER CHECK(Year >= 1900)",
        "EngineSize": "REAL CHECK(EngineSize > 0)",
        "Additional": "TEXT",
        "FOREIGN KEY(ItemID)": "REFERENCES RepairItems(ItemID)"
    }, replace=True)

    # Products (things for sale)
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

    # SoldItems (many-to-many Sales ↔ Products)
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

def populateDatabase():
    db = DatabaseManager("austinDB.db")

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

    # Customers (10)
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

    # RepairItems (10)
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

    # Products (10)
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

    # Sales (10)
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

    # SoldItems (10)
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

    # CarDetails (for 5 cars)
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


    # RepairJobs (10)
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

    # RepairItemParts (10)
    repairItemParts = [
        (1, 1, 1),  # Gaming PC used 1x Intel i5 CPU
        (1, 2, 1),  # Gaming PC used 1x GTX 1660
        (3, 4, 1),  # Office Laptop used 1x RAM stick
        (5, 7, 1),  # Workstation used 1x PSU
        (7, 9, 1),  # Server PC used 1x Intel i7
        (9, 5, 1),  # MacBook repair used 1x SSD
        (2, 6, 2),  # Toyota repair used 2x HDDs (for infotainment data backup maybe)
        (4, 8, 1),  # Mazda repair used 1x Case part
        (6, 10, 1), # Honda repair used 1x RTX 3060 (pretend GPU for car display system)
        (10, 3, 1)  # Commodore repair used 1x Ryzen CPU (improvised swap)
    ]
    for rip in repairItemParts:
        db.insert("RepairItemParts", {
            "ItemID": rip[0],
            "PartID": rip[1],
            "Quantity": rip[2]
        })

    db.close()
    print("Database populated with 10 dummy entries per table")

setupDatabase()
populateDatabase()

