from datetime import date, datetime
import csv
import os

# -------------------------
# FUNCTIONS
# -------------------------


def calculate_workload(classes,assignments,exams,work_hours):
    score = (
    (classes*5)+
    (assignments*5)+
    (exams*10)+
    (work_hours)
)
    return score

def get_wokrload_level(score):
    if score <40:
        return "Low"
    elif score <70:
        return "Medium"
    else:
        return "High"

def days_until_due(due_date):
    today = date.today()
    difference = due_date - today

    return difference.days

def get_deadline_status(days_remaining):
    if days_remaining < 0:
        return "Overdue"

    elif days_remaining == 0:
        return "Due Today"

    elif days_remaining <= 2:
        return "Due Soon"

    else:
        return "Upcoming"

def calculate_priority(days_remaining, difficulty):
    if difficulty == "High":
        if days_remaining <= 2:
            return "Critical"
        elif days_remaining <= 5:
            return "High"
        else:
            return "Medium"
        
    elif difficulty == "Medium":
        if days_remaining <= 2:
            return "High"
        elif days_remaining <= 5:
            return "Medium"
        else:
            return "Low"

    elif difficulty == "Low":
        if days_remaining <= 2:
            return "Medium"
        elif days_remaining <= 5:
            return "Low"
        else:
            return "Low"

def display_assignment(assignment):
    days_remaining = days_until_due(assignment["due"])
    status = get_deadline_status(days_remaining)
    priority = calculate_priority(days_remaining, assignment["difficulty"])

    print("\n----------------------")
    print("Assignment:", assignment["name"])
    print("Course:", assignment["course"])
    print("Due:", assignment["due"])
    print("Days remaining:", days_remaining)
    print("Difficulty:", assignment["difficulty"])
    print("Status:", status)
    print("Priority:", priority)

def add_assignment(assignments):
    name = input("Assignment name: ")
    course = input("Course: ")
    due_date_input = input("Due date (YYYY-MM-DD): ")
    due_date = datetime.strptime(due_date_input, "%Y-%m-%d").date()
    difficulty = input("Difficulty (High/Medium/Low): ")
    estimated_hours = float(input("Estimated hours: "))

    assignment = {
    "name": name,
    "course": course,
    "due": due_date,
    "difficulty": difficulty,
    "estimated_hours": estimated_hours
    }
    assignments.append(assignment)
    save_assignments(assignments)
    print("Assignment added successfully!")

def display_assignments(assignments):
    if not assignments:
        print("No assignments found.")
    for assignment in assignments:
        display_assignment(assignment)

def show_high_priority(assignments):
    for assignment in assignments:
        days_remaining = days_until_due(assignment["due"])
        priority = calculate_priority(days_remaining, assignment["difficulty"])

        if priority == "High" or priority == "Critical":
            display_assignment(assignment)

def remove_assignment(assignments):
    found = False
    name = input("Enter the assignment name to remove: ")

    for assignment in assignments:
        if assignment["name"]==name:
            assignments.remove(assignment)
            save_assignments(assignments)
            print("Assignment removed successfully!")
            found = True

    if not found:
        print("Assignment not found.")

def save_assignments(assignments):
        with open("assignments.csv", "w", newline="") as file:
            fieldnames = ["name", "course", "due", "difficulty", "estimated_hours"]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for assignment in assignments:
                assignment_copy = assignment.copy()
                assignment_copy["due"] = assignment["due"].isoformat()
                writer.writerow(assignment_copy)

def load_assignments():
    if not os.path.exists("assignments.csv"):
        return []
    
    with open("assignments.csv", "r", newline="") as file:
        reader = csv.DictReader(file)
        assignments = []

        for row in reader:
            assignment = {
                "name": row["name"],
                "course": row["course"],
                "due": datetime.strptime(row["due"], "%Y-%m-%d").date(),
                "difficulty": row["difficulty"],
                "estimated_hours": float(row["estimated_hours"])
            }

            assignments.append(assignment)

    return assignments

# -------------------------
# MAIN PROGRAM
# -------------------------

print("==================================")
print("       Welcome to NinerLife")
print("==================================")

name = input("What is your name? ")
classes = int(input("How many classes are you taking? "))
work_hours = float(input("How many hours do you work per week? "))
assignments = int(input("How many assignments do you have this week? "))

assignment_list=[]
for i in range (assignments):
    assignment_name = input("Enter an assignment: ")
    assignment_list.append(assignment_name)

exams= int(input("How many exams do you have this week ? "))

student = {
    "name": name,
    "classes": classes,
    "work_hours": work_hours,
    "assignments": assignments,
    "assignment_list": assignment_list,
    "exams": exams
}

workload_score= calculate_workload(classes,assignments,exams,work_hours)
level=get_wokrload_level(workload_score)

print("\n================================")
print("          YOUR RESULTS")
print("================================")


print("\nWelcome,", name)
print("Classes:", classes)
print("Work hours:", work_hours)
print("Assignments:", assignments)
print("Assignment List:", assignment_list)
print("Exams:", exams)


print("\nYour workload score is:", workload_score)
print("Workload Level:",level)

if level == "Low":
    print("You have a manageable week. Keep up the good work!")
elif level == "Medium":
    print("Your week looks somewhat busy. Make sure you plan your time.")
else:
    print("Your week looks very busy. Consider prioritizing your deadlines.")


print("\nStudent Information:")
print(student)
print("Student Name:", student["name"])
print("Student Assignments:", student["assignment_list"])

assignments = load_assignments()

display_assignments(assignments)

show_high_priority(assignments)

remove_assignment(assignments)
# add_assignment(assignments)

while True:
    print("\n===== NinerLife Menu =====")
    print("1. Display Assignments")
    print("2. Show High Priority")
    print("3. Remove Assignment")
    print("4. Add Assignment")
    print("5. Exit")

    choice = input("Enter your choice: ")

    if choice == "1":
        display_assignments(assignments)

    elif choice == "2":
        show_high_priority(assignments)

    elif choice == "3":
        remove_assignment(assignments)

    elif choice == "4":
        add_assignment(assignments)

    elif choice == "5":
        print("Thank you for using NinerLife!")
        break

save_assignments(assignments)
print("Assignments saved!")