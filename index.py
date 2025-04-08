import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from datetime import datetime, timedelta, date
import matplotlib.pyplot as plt
from collections import Counter

# ─── Connect to MySQL ─────────────────────────────────────────────────────────
conn = mysql.connector.connect(
    host="localhost", user="root", password="root", database="blood_bank"
)
cursor = conn.cursor()

# ─── Compatibility ────────────────────────────────────────────────────────────
compatible = {
    "A+": ["A+", "A-", "O+", "O-"], "A-": ["A-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"], "B-": ["B-", "O-"],
    "AB+": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
    "AB-": ["A-", "B-", "AB-", "O-"],
    "O+": ["O+", "O-"], "O-": ["O-"]
}

# ─── Setup ────────────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("Blood Donation Directory")
root.geometry("1200x750")
style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", padding=6, font=('Helvetica', 10, 'bold'))
style.configure("TLabel", font=('Helvetica', 10))
style.configure("TEntry", padding=5)

notebook = ttk.Notebook(root)
notebook.pack(padx=20, pady=20, fill="both", expand=True)

# ─── Helper ───────────────────────────────────────────────────────────────────
def clear_entries(entries):
    for entry in entries:
        entry.delete(0, tk.END)

# ─── Data ─────────────────────────────────────────────────────────────────────
genders = ["Male", "Female", "Other"]
blood_groups = list(compatible.keys())
locations = ["Chennai", "Delhi", "Mumbai", "Bangalore", "Other"]

# ─── Add Donor Tab ────────────────────────────────────────────────────────────
donor_tab = ttk.Frame(notebook)
notebook.add(donor_tab, text="Add Donor")

donor_frame = ttk.LabelFrame(donor_tab, text="Donor Information", padding=20)
donor_frame.pack(padx=40, pady=30, fill="x")

labels = ["Name", "Age", "Gender", "Contact", "Location", "Blood Group", "Last Donation (YYYY-MM-DD)", "Donated To (Receiver)"]
fields = []

for i, text in enumerate(labels):
    ttk.Label(donor_frame, text=text).grid(row=i, column=0, sticky="w", pady=5)
    if text == "Gender":
        entry = ttk.Combobox(donor_frame, values=genders, state="readonly")
    elif text == "Blood Group":
        entry = ttk.Combobox(donor_frame, values=blood_groups, state="readonly")
    elif text == "Location":
        entry = ttk.Combobox(donor_frame, values=locations, state="readonly")
    else:
        entry = ttk.Entry(donor_frame)
    entry.grid(row=i, column=1, pady=5, sticky="ew")
    fields.append(entry)

def add_donor():
    values = [field.get().strip() for field in fields]
    if not all(values[:-1]):
        return messagebox.showerror("Error", "All fields except Receiver must be filled.")
    try:
        donation_date = datetime.strptime(values[6], "%Y-%m-%d").date()
    except:
        return messagebox.showerror("Error", "Invalid date format (YYYY-MM-DD)")

    cursor.execute("SELECT last_donation_date FROM donor WHERE name=%s ORDER BY last_donation_date DESC LIMIT 1", (values[0],))
    row = cursor.fetchone()
    if row:
        last_date = row[0]
        if isinstance(last_date, datetime):
            last_date = last_date.date()
        if (donation_date - last_date).days < 180:
            return messagebox.showerror("Error", f"Wait 180 days. Last donation was on: {last_date}")

    receiver_id = None
    if values[7]:
        cursor.execute("SELECT id FROM receiver WHERE name=%s", (values[7],))
        rec = cursor.fetchone()
        if rec:
            receiver_id = rec[0]

    cursor.execute("""
        INSERT INTO donor(name, age, gender, contact, location, blood_group, last_donation_date, receiver_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (*values[:7], receiver_id))
    conn.commit()

    if receiver_id:
        donor_id = cursor.lastrowid
        cursor.execute("INSERT INTO donation(donor_id, receiver_id, donation_date) VALUES (%s,%s,%s)",
                       (donor_id, receiver_id, values[6]))
        conn.commit()

    messagebox.showinfo("Success", "Donor Added Successfully!")
    clear_entries(fields)

ttk.Button(donor_frame, text="Add Donor", command=add_donor).grid(row=len(labels), columnspan=2, pady=15)

# ─── Add Receiver Tab ─────────────────────────────────────────────────────────
receiver_tab = ttk.Frame(notebook)
notebook.add(receiver_tab, text="Add Receiver")

receiver_frame = ttk.LabelFrame(receiver_tab, text="Receiver Information", padding=20)
receiver_frame.pack(padx=40, pady=30, fill="x")

receiver_labels = ["Name", "Age", "Gender", "Contact", "Location", "Blood Group", "Required Type", "Date of Need"]
receiver_fields = []

for i, text in enumerate(receiver_labels):
    ttk.Label(receiver_frame, text=text).grid(row=i, column=0, sticky="w", pady=5)
    if text == "Gender":
        entry = ttk.Combobox(receiver_frame, values=genders, state="readonly")
    elif text == "Blood Group" or text == "Required Type":
        entry = ttk.Combobox(receiver_frame, values=blood_groups, state="readonly")
    elif text == "Location":
        entry = ttk.Combobox(receiver_frame, values=locations, state="readonly")
    else:
        entry = ttk.Entry(receiver_frame)
    entry.grid(row=i, column=1, pady=5, sticky="ew")
    receiver_fields.append(entry)

def add_receiver():
    values = [f.get().strip() for f in receiver_fields]
    if not all(values):
        return messagebox.showerror("Error", "Fill all fields")
    cursor.execute("""
        INSERT INTO receiver(name, age, gender, contact, location, blood_group, required_type, date_of_need)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, values)
    conn.commit()
    messagebox.showinfo("Success", "Receiver Added")
    clear_entries(receiver_fields)

ttk.Button(receiver_frame, text="Add Receiver", command=add_receiver).grid(row=len(receiver_labels), columnspan=2, pady=15)

# ─── View Donors Tab ──────────────────────────────────────────────────────────
view_tab = ttk.Frame(notebook)
notebook.add(view_tab, text="View Donors")

view_frame = ttk.LabelFrame(view_tab, text="Filter and View Donors", padding=20)
view_frame.pack(padx=40, pady=30, fill="both", expand=True)

filter_frame = ttk.Frame(view_frame)
filter_frame.pack(pady=10)

search_name = ttk.Entry(filter_frame)
search_name.grid(row=0, column=1, padx=5)
ttk.Label(filter_frame, text="Name:").grid(row=0, column=0, padx=5)

filter_bg = ttk.Combobox(filter_frame, values=[""] + blood_groups, state="readonly")
filter_bg.grid(row=0, column=3, padx=5)
ttk.Label(filter_frame, text="Blood Group:").grid(row=0, column=2, padx=5)

filter_loc = ttk.Combobox(filter_frame, values=[""] + locations, state="readonly")
filter_loc.grid(row=0, column=5, padx=5)
ttk.Label(filter_frame, text="Location:").grid(row=0, column=4, padx=5)

table = ttk.Treeview(view_frame, columns=("Name", "Age", "Gender", "Contact", "Location", "Blood Group", "Last Donation"), show="headings")
for col in table["columns"]:
    table.heading(col, text=col)
    table.column(col, width=120)
table.pack(fill="both", expand=True, pady=10)

def load_donors():
    q = "SELECT name, age, gender, contact, location, blood_group, last_donation_date FROM donor WHERE 1=1"
    filters = []
    params = []
    if search_name.get().strip():
        filters.append("name LIKE %s")
        params.append(f"%{search_name.get().strip()}%")
    if filter_bg.get().strip():
        filters.append("blood_group = %s")
        params.append(filter_bg.get().strip())
    if filter_loc.get().strip():
        filters.append("location = %s")
        params.append(filter_loc.get().strip())
    if filters:
        q += " AND " + " AND ".join(filters)
    cursor.execute(q, params)
    results = cursor.fetchall()
    table.delete(*table.get_children())
    for row in results:
        table.insert("", tk.END, values=row)

ttk.Button(filter_frame, text="Search", command=load_donors).grid(row=0, column=6, padx=10)
load_donors()

# ─── Final ────────────────────────────────────────────────────────────────────
root.mainloop()

