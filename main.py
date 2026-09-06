print("================================")
print("       Welcome to NinerLife")
print("================================")

name = input("What is your name? ")
classes = int(input("How many classes are you taking? "))
work_hours = float(input("How many hours do you work per week? "))
assignments = int(input("How many assignments do you have this week? "))
exams= int(input("How many emaxams do you have this week ? "))

workload_score=(
    (classes*5)+(assignments*5)+(exams*10)+(work_hours)
)

if workload_score<40:
    workload_level ="Low"

elif workload_score<70:
    workload_level ="Medium"

else:
    workload_level="High"

print("\n================================")
print("          YOUR RESULTS")
print("================================")


print("\nWelcome,", name)
print("Classes:", classes)
print("Work hours:", work_hours)
print("Assignments:", assignments)
print("Exams:", exams)


print("\nYour workload score is:", workload_score)
print("Workload Level:", workload_level)

if workload_level == "Low":
    print("You have a manageable week. Keep up the good work!")

elif workload_level == "Medium":
    print("Your week looks somewhat busy. Make sure you plan your time.")

else:
    print("Your week looks very busy. Consider prioritizing your deadlines.")