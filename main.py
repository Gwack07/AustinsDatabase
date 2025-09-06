from databaseManager import DatabaseManager

def displayRecords(db, tableName):
    """Display all records in a table with column headers."""
    try:
        rows = db.query(f"SELECT * FROM {tableName}")
        if rows:
            columns = [desc[0] for desc in db.cursor.description]
            print("\n" + " | ".join(columns))
            print("-" * 50)
            for r in rows:
                print(" | ".join([str(i) if i is not None else "" for i in r]))
        else:
            print(f"No records in {tableName}.")
    except Exception as e:
        print(f"Error: {e}")

def getInputForTable(db, tableName):
    """Get input for a table from user, showing required/optional fields."""
    columns = db.query(f"PRAGMA table_info({tableName})")
    data = {}
    for col in columns:
        name = col[1]
        required = col[3] == 1  # not null
        if col[5]:  # primary key autoincrement
            continue
        prompt = f"{name} ({'Required' if required else 'Optional'}): "
        value = input(prompt)
        if value.strip() == "/":
            print("Cancelled. Returning to menu.")
            return
        if required and not value:
            print(f"{name} is required!")
            return None
        if value:
            data[name] = value
    return data

def addRecord(db):
    displayTables(db)
    choice = input("Choose table number to add record: ")
    if choice.strip() == "/":
        print("Cancelled. Returning to menu.")
        return
    tableName = tableList[int(choice)-1]

    # Special case for CarDetails
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
        return  # Exit function after handling this special case

    # Special case for ComputerDetails
    elif tableName.lower() == "computerdetails":
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

    # Generic case for all other tables
    data = getInputForTable(db, tableName)
    if data:
        try:
            db.insert(tableName, data)
        except Exception as e:
            print(f"Error inserting: {e}")


def updateRecord(db):
    displayTables(db)
    choice = input("Choose table number to update record: ")
    if choice.strip() == "/":
        print("Cancelled. Returning to menu.")
        return
    tableName = tableList[int(choice)-1]
    condition = input("Enter condition for record to update (e.g., ItemID=1): ")
    columns = db.query(f"PRAGMA table_info({tableName})")
    updates = {}
    for col in columns:
        name = col[1]
        if col[5]:  # skip primary key
            continue
        required = col[3] == 1
        prompt = f"New value for {name} ({'Required' if required else 'Optional'}): "
        value = input(prompt)
        if value:
            updates[name] = value
    if updates:
        try:
            db.updateRecord(tableName, updates, condition)
        except Exception as e:
            print(f"Error updating: {e}")

def deleteRecord(db):
    displayTables(db)
    choice = input("Choose table number to delete record: ")
    if choice.strip() == "/":
        print("Cancelled. Returning to menu.")
        return
    tableName = tableList[int(choice)-1]
    condition = input("Enter condition for record to delete (e.g., ItemID=1): ")
    db.deleteRecord(tableName, condition)

def customQuery(db):
    query = input("Enter your SQL query: ")
    displayQueryResults(db, query)

def miscQueries(db):
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
         "SELECT * FROM RepairItems r JOIN RepairJobs j ON r.ItemID=j.RepairItemID WHERE r.RepairType='Com1puter' AND j.DateReceived >= date('now','-7 days')"),
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
    for i, q in enumerate(queries, 1):
        print(f"{i}. {q[0]}")

    choice = int(input("Choose query number: ")) - 1
    if 0 <= choice < len(queries):
        displayQueryResults(db, queries[choice][1])
    else:
        print("Invalid choice.")

def displayQueryResults(db, query):
    try:
        db.cursor.execute(query)
        rows = db.cursor.fetchall()
        if rows:
            columns = [desc[0] for desc in db.cursor.description]
            print("\n" + " | ".join(columns))
            print("-"*50)
            for r in rows:
                print(" | ".join([str(i) if i is not None else "" for i in r]))
        else:
            print("No results.")
    except Exception as e:
        print(f"Error: {e}")

def displayTables(db):
    global tableList
    tableList = ["Suppliers", "Parts", "PartSuppliers", "Customers", "RepairItems",
                 "CarDetails", "ComputerDetails", "RepairJobs", "RepairItemParts",
                 "Products", "Sales", "SoldItems"]
    print("\n--- Tables ---")
    for i, t in enumerate(tableList, 1):
        print(f"{i}. {t}")

def main():
    db = DatabaseManager("austinDB.db")
    while True:
        print("\n--- Austin's Database Console ('/' to cancel) ---")
        print("1. View Records")
        print("2. Add Record")
        print("3. Update Record")
        print("4. Delete Record")
        print("5. Custom Query")
        print("6. Miscellaneous Queries")
        print("7. Exit")

        choice = input("Select an option: ")

        if choice == "1":
            displayTables(db)
            tableChoice = int(input("Choose table number: ")) - 1
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
            db.close()
            break
        else:
            print("Invalid option. Try again.")

if __name__ == "__main__":
    main()
