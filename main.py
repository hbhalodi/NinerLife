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


# -------------------------
# MAIN PROGRAM
# -------------------------

print("================================")
print("       Welcome to NinerLife")
print("================================")

name = input("What is your name? ")
classes = int(input("How many classes are you taking? "))
work_hours = float(input("How many hours do you work per week? "))
assignments = int(input("How many assignments do you have this week? "))
exams= int(input("How many emaxams do you have this week ? "))

workload_score= calculate_workload(classes,assignments,exams,work_hours)


level=get_wokrload_level(workload_score)

print("\n================================")
print("          YOUR RESULTS")
print("================================")


print("\nWelcome,", name)
print("Classes:", classes)
print("Work hours:", work_hours)
print("Assignments:", assignments)
print("Exams:", exams)


print("\nYour workload score is:", workload_score)
print("Workload Level:",level)

if level == "Low":
    print("You have a manageable week. Keep up the good work!")

elif level == "Medium":
    print("Your week looks somewhat busy. Make sure you plan your time.")

else:
    print("Your week looks very busy. Consider prioritizing your deadlines.")