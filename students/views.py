from django.shortcuts import render,redirect
from django.views.generic import View
from django.db.models import Q
from django.contrib import messages
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required

import datetime

from dvm.decorators import student_required,StudentLoginRequiredMixin
from professors.models import Courses,CourseList,Announcements,Content,Evals,Branch,Semester
from .models import Students
from .forms import ProfileCreationForm

def get_current_sem():
    todays_date = datetime.date.today()
    try:
        curr_sem=Semester.objects.get(start_date__lt=todays_date,end_date__gt=todays_date)
        return curr_sem
    except Semester.DoesNotExist:
        return Semester.objects.filter(end_date__lt=todays_date).order_by("-end_date")[0]

class ProfileCreationView(StudentLoginRequiredMixin,View):
    def get(self,request):
        form = ProfileCreationForm()
        return render(request,"students/create.html",{
            "form":form,
        })
    def post(self,request):
        form = ProfileCreationForm(request.POST,request.FILES)
        if form.is_valid():
            curr_user = request.user
            new_profile = Students(
                user =curr_user,
                bitsid = form.cleaned_data.get('bitsid'),
            )
            new_profile.save()
            return redirect("stu-home")
        return render(request,"students/create.html",{
            "form":form,
        })

@student_required
def home(request):
    try:
        curr_user = Students.objects.get(user=request.user)
        user_courses = Courses.objects.filter(student=curr_user,sem=get_current_sem())
        return render(request,"students/home.html",{
            "courses":user_courses,
        })
    except Students.DoesNotExist:
        return redirect("create-profile")

@login_required 
def course_detail(request,pk,prof=False):
    selected_course = CourseList.objects.get(pk=pk)
    course_annoucements = Announcements.objects.filter(course=selected_course,sem=get_current_sem())
    course_content = Content.objects.filter(course=selected_course,sem=get_current_sem())
    if prof:
        evals = Evals.objects.filter(course=selected_course,sem=get_current_sem()).distinct()
        if Courses.objects.filter(~Q(grade=None),course = selected_course,sem=get_current_sem()).exists():
            stu_grade = True
        else:
            stu_grade = False
    else:
        curr_student = Students.objects.get(user=request.user)
        stu_grade = Courses.objects.get(course=selected_course,student=curr_student,sem=get_current_sem()).grade
        evals = Evals.objects.filter(student=curr_student,course=selected_course,sem=get_current_sem())
    return render(request,"students/course-detail.html",{
        "course":selected_course,
        "annoucements":course_annoucements,
        "contents":course_content,
        "prof":prof,
        "evals":evals,
        "grade":stu_grade,
    })

@student_required
def course_registration(request):
    curr_sem = get_current_sem()
    todays_date = datetime.date.today()
    if (curr_sem.reg_date==todays_date) or (curr_sem.reg_date_last==todays_date):

        curr_student = Students.objects.get(user=request.user)
        br = curr_student.bitsid[4:6]
        year = curr_student.bitsid[:4]

        def get_branch_cdcs(br,cdc):
            branch = Branch.objects.get(branch_code=br)
            cdcs = CourseList.objects.filter(branch=branch,cdcs=cdc)
            return cdcs

        fy_course_1 = ["BITS F110","CHEM F111","PHY F111","EEE F111"]
        fy_course_2 = ["BITS F112","ME F112","CS F111","BIO F111","BIO F110"]
        if (todays_date.year - int(year))<1:
            sem = "FY1"
            fy_cdcs = CourseList.objects.filter(cdcs="FY")
            cc =["CHEM F110","BITS F111","PHY F110","MATH F111"]
            if br in ["B1","B2","B3","B4","B5","A2"]:
                fy_course_1+=cc
                cdcs = fy_cdcs.filter(course_id__in = fy_course_1)
            else:
                fy_course_2+=cc
                cdcs = fy_cdcs.filter(course_id__in = fy_course_2)
        elif (todays_date.year - int(year))==1:
            if todays_date<datetime.date(todays_date.year,8,1):
                sem="FY2"
                cc = ["MATH F112","MATH F113",]
                fy_cdcs = CourseList.objects.filter(cdcs="FY")
                if br in ["B1","B2","B3","B4","B5","A2"]:
                    fy_course_2+=cc
                    cdcs = fy_cdcs.filter(course_id__in = fy_course_2)
                else:
                    fy_course_1+=cc
                    cdcs = fy_cdcs.filter(course_id__in = fy_course_1)

            else:
                sem="SY1"
                cdcs = get_branch_cdcs(br,cdc=sem)

        elif (todays_date.year - int(year))==2:
            if todays_date<datetime.date(todays_date.year,8,1):
                sem="SY2"
                cdcs = get_branch_cdcs(br,cdc=sem)
            else:
                sem="TY1"
                cdcs = get_branch_cdcs(br,cdc=sem)
        elif (todays_date.year - int(year))==3:
            if todays_date<datetime.date(todays_date.year,8,1):
                sem="TY2"
                cdcs = get_branch_cdcs(br,cdc=sem)
            else:
                sem="4Y1"
                cdcs = get_branch_cdcs(br,cdc=sem)
        elif (todays_date.year - int(year))==4:
            if todays_date<datetime.date(todays_date.year,8,1):
                sem="4Y2"
                cdcs = get_branch_cdcs(br,cdc=sem)
            else:
                sem="5Y1"
                cdcs = get_branch_cdcs(br,cdc=sem)
        elif (todays_date.year - int(year))==5:
            if todays_date<datetime.date(todays_date.year,8,1):
                sem="5Y2"
                cdcs = get_branch_cdcs(br,cdc=sem)

        branch = Branch.objects.get(branch_code=br)
        dels = CourseList.objects.filter(dept=branch.dept,electives="DEL")
        opel = CourseList.objects.filter(electives="OPEL")
        hel = CourseList.objects.filter(electives="HEL")

        for cdc in cdcs:
            try:
                Courses.objects.create(course=cdc,student=curr_student,marks=0,sem=curr_sem)
            except IntegrityError:
                continue

        enrolled_courses=Courses.objects.filter(student=curr_student,date_added=todays_date,sem=curr_sem)
        total_credits=0
        for course in enrolled_courses:
            total_credits+=course.course.credit
        
        return render(request,"students/course-registration.html",{
            "cdcs":cdcs,
            "dels":dels,
            "opels":opel,
            "hels":hel,
            "enrol_courses":enrolled_courses,
            "total_credits":total_credits,
        })
    
    else:
        messages.error(request,"Registration is not open at the moment.")
        return redirect("stu-home")

@student_required
def add_enrolled_course(request,pk):
    curr_student = Students.objects.get(user=request.user)
    enrolled_courses=Courses.objects.filter(student=curr_student,date_added=datetime.date.today())
    total_credits=0
    for course in enrolled_courses:
        if course.course == pk:
            messages.error(request,"This course has already been added.")
            return redirect("course-reg")
        total_credits+=course.course.credit
    if total_credits==25:
        messages.error(request,"You can't add more courses.You've already reached maximum no of units in one semester,25.")
        return redirect("course-reg")
    
    selected_course = CourseList.objects.get(pk=pk)


    if total_credits+selected_course.credit>=25:
        messages.error(request,"You can't add this course since the total sum of credits of all your courses including this one is exceeding 25 units.")
        return redirect("course-reg")
    
    Courses.objects.create(course=selected_course,student=curr_student,marks=0,sem=get_current_sem())
    messages.success(request,f"Your {selected_course.course_name} has been successfully added.")
    return redirect("course-reg")