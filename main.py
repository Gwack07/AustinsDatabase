from databaseManager import DatabaseManager
from datetime import datetime

DB_NAME = "austinDB.db"

def mainMenu():
    print("\n--- Austin's Database Management ---")
    print("1. View Records")
    print("2. Add Record")
    print("3. Update Record")
    print("4. Delete Record")
    print("5. Exit")
    return input("Choose an option: ")

def tableMenu():
    print("\nSelect Table:")
    tables = [
        "Suppliers", "Parts", "PartSuppliers", "Customers", "RepairItems",
        "CarDetails", "ComputerDetails", "RepairJobs", "RepairItemParts",
        "Products", "Sales", "SoldItems"
    ]
    for i, t in enumerate(tables, 1):
        print(f"{i}. {t}")
    choice = input("Choose table number: ")
    try:
        idx = int(choice) - 1
        return tables[idx]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return None

def displayRecords(db, table):
    records = db.getAllRecords(table)
    if records:
        columns = [col[1] for col in db.query(f"PRAGMA table_info({table})")]
        # Print header
        header = " | ".join(columns)
        print(f"\n--- Records in {table} ---")
        print(header)
        print("-" * len(header))
        # Print each record aligned with columns
        for r in records:
            row = " | ".join([str(item) if item is not None else "" for item in r])
            print(row)
    else:
        print(f"No records found in {table}.")


def addRecord(db, table):
    data = {}
    print(f"\nAdding record to {table}.")
    columns = db.query(f"PRAGMA table_info({table})")
    for col in columns:
        colName = col[1]
        notNull = col[3]
        defaultVal = col[4]
        if colName.lower().endswith("id") and "autoincrement" in col[2].lower():
            continue  # skip auto-incremented primary key

        reqText = "Required" if notNull else "Optional"
        prompt = f"{colName} ({reqText})"
        if defaultVal:
            prompt += f" [default: {defaultVal}]"
        value = input(f"{prompt}: ")

        if value == "" and notNull:
            print(f"{colName} is required. Record not added.")
            return
        if value != "":
            if col[2].startswith("INTEGER"):
                value = int(value)
            elif col[2].startswith("REAL"):
                value = float(value)
            data[colName] = value
    try:
        db.insert(table, data)
    except Exception as e:
        print(f"Error inserting record: {e}")


def updateRecord(db, table):
    condition = input(f"Enter condition for record to update (e.g., SupplierID=1): ")
    updates = {}
    columns = db.query(f"PRAGMA table_info({table})")

    print("\nEnter new values for columns (leave blank to skip):")
    for col in columns:
        colName = col[1]
        notNull = col[3]

        # Skip primary key auto-increment columns
        if col[5] == 1:  # PK
            continue

        reqText = "Required" if notNull else "Optional"
        value = input(f"{colName} ({reqText}): ").strip()
        if value != "":
            # Convert types
            if col[2].startswith("INTEGER"):
                value = int(value)
            elif col[2].startswith("REAL"):
                value = float(value)
            updates[colName] = value

    if updates:
        try:
            db.updateRecord(table, updates, condition)
        except Exception as e:
            print(f"Error updating record: {e}")
    else:
        print("No updates provided.")


def deleteRecord(db, table):
    condition = input(f"Enter condition for record to delete (e.g., ItemID=1): ")
    try:
        db.deleteRecord(table, condition)
    except Exception as e:
        print(f"Error deleting record: {e}")

def run():
    db = DatabaseManager(DB_NAME)
    while True:
        choice = mainMenu()
        if choice == "1":  # View
            table = tableMenu()
            if table:
                displayRecords(db, table)
        elif choice == "2":  # Add
            table = tableMenu()
            if table:
                addRecord(db, table)
        elif choice == "3":  # Update
            table = tableMenu()
            if table:
                updateRecord(db, table)
        elif choice == "4":  # Delete
            table = tableMenu()
            if table:
                deleteRecord(db, table)
        elif choice == "5":
            print("Exiting...")
            db.close()
            break
        else:
            print("Invalid option, try again.")

if __name__ == "__main__":
    run()
