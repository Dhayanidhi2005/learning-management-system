from django.shortcuts import render,redirect,get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.views.generic import View
from django.views.generic.edit import CreateView,UpdateView,DeleteView
from django.core.mail import send_mail

import dvm.settings as settings
from dvm.decorators import professor_required,ProfessorLoginRequiredMixin
from students.views import course_detail,get_current_sem
from students.models import Students
from .models import Professors,CourseList,Announcements,Courses,Evals,Content
from .forms import AddAnnouncementForm,AddContentForm,AddEvalsForm,AddMarksForm,AddGradesForm,AddCourseForm,AddStudentsForm,UpdateStudentMarks
# Create your views here.

@professor_required
def home(request):
    user_courses = Professors.objects.get(prof=request.user).courses.all()
    return render(request,"students/home.html",{
        "courses":user_courses,
        "prof":True,
    })

@professor_required
def add_announcements(request,pk):
    if request.method=="POST":
        form = AddAnnouncementForm(request.POST,request.FILES)
        if form.is_valid():
            req_course = CourseList.objects.get(pk=pk)
            req_prof = Professors.objects.get(prof=request.user)
            new_ann = Announcements(
                title = form.cleaned_data['title'],
                msg = form.cleaned_data['msg'],
                attachments = form.cleaned_data['attachments'],
                prof = req_prof,
                course = req_course,
                sem=get_current_sem(),
            )
            subject = req_course.course_name+":"+form.cleaned_data['title']
            message = form.cleaned_data['msg']+"\nfrom:"+str(req_prof)
            from_email =  "f20231017@pilani.bits-pilani.ac.in"
            recipient_list = []
            email_queryset = Students.objects.filter(courses__course__pk=pk).values("user__email")
            for email in email_queryset:
                recipient_list.append(email["user__email"])
            send_mail(subject,message,from_email,recipient_list)
            print(subject,message,from_email,recipient_list)
            new_ann.save()
            return redirect("prof-coursedetail",pk=req_course.pk)
    form = AddAnnouncementForm()
    return render(request,"students/create.html",{
        "form":form,
        "prof":True,
    })

class ContentCreateView(ProfessorLoginRequiredMixin,View):
    def get(self,request,*args, **kwargs):
        form = AddContentForm()
        return render(request,"students/create.html",{
            "form":form,
            "prof":True,
        })
    
    def post(self,request,*args, **kwargs):
        form = AddContentForm(request.POST,request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.course = CourseList.objects.get(pk=kwargs["pk"])
            obj.sem=get_current_sem()
            obj.save()
            return redirect("prof-coursedetail",pk=kwargs["pk"])
        return render(request,"students/create.html",{
            "form":form,
            "prof":True,
        })
    
class EvalCreateView(ProfessorLoginRequiredMixin,CreateView):
    form_class = AddEvalsForm
    template_name = "students/create.html"
    extra_context = {"prof":True}

    def form_valid(self, form) :
        form.instance.course = CourseList.objects.get(pk=self.kwargs['pk'])
        form.instance.sem=get_current_sem()
        req_stu_course = Courses.objects.get(course=form.instance.course,student=form.instance.student)
        req_stu_course.marks +=form.instance.marks
        req_stu_course.save()
        return super(EvalCreateView,self).form_valid(form)

    def get_success_url(self):
        return reverse("prof-coursedetail",kwargs={"pk":self.kwargs['pk']})
    
class AddMarkView(ProfessorLoginRequiredMixin,CreateView):
    form_class = AddMarksForm
    template_name = "students/create.html"
    extra_context = {"prof":True}

    def get_form_kwargs(self,**kwargs):
        #gets the current course id
        form_kwargs = super(AddMarkView, self).get_form_kwargs(**kwargs)
        form_kwargs["course_pk"] = self.kwargs["pk"]
        return form_kwargs

    def form_valid(self, form) :
        #for adding instance of course before saving the object
        form.instance.course = CourseList.objects.get(pk=self.kwargs['pk'])
        # for adding the eval's mark to course total
        req_stu_course = Courses.objects.get(course=form.instance.course,student=form.instance.student)
        req_stu_course.marks +=form.instance.marks
        req_stu_course.save()
        ex_eval = Evals.objects.get(title=self.kwargs['title'])
        form.instance.title = ex_eval.title
        form.instance.total_marks = ex_eval.total_marks
        form.instance.sem=get_current_sem()
        return super(AddMarkView,self).form_valid(form)

    def get_success_url(self):
        return reverse("prof-coursedetail",kwargs={"pk":self.kwargs['pk']})

@professor_required 
def add_final_grade(request,pk):
    if request.method=="POST":
        form = AddGradesForm(request.POST)
        if form.is_valid():
            req_courses = Courses.objects.filter(course=pk).order_by("marks")
            list_val = list(form.cleaned_data.values())
            if req_courses.count()!=sum(list_val):
                messages.error(request,"Kindly ensure that the sum of all the given fields equals the number of students enrolled in the course")
                return render(request,"students/create.html",{"form":form})
            
            no=0
            for course in req_courses:
                if no<sum(list_val[0:1]):
                    course.grade="A"
                elif sum(list_val[0:1])<=no<sum(list_val[0:2]):
                    course.grade="A-"
                elif sum(list_val[0:2])<=no<sum(list_val[0:3]):
                    course.grade="B"
                elif sum(list_val[0:3])<=no<sum(list_val[0:4]):
                    course.grade="B-"
                elif sum(list_val[0:4])<=no<sum(list_val[0:5]):
                    course.grade="C"
                elif sum(list_val[0:5])<=no<sum(list_val[0:6]):
                    course.grade="C-"
                elif sum(list_val[0:6])<=no<sum(list_val[0:7]):
                    course.grade="D"
                elif sum(list_val[0:7])<=no<sum(list_val[0:8]):
                    course.grade="E"
                elif sum(list_val[0:8])<=no:
                    course.grade="NC"
                course.save()
                no+=1

            return redirect("prof-coursedetail",pk=pk)
    form = AddGradesForm()
    return render(request,"students/create.html",{
        "form":form,
        "prof":True,
    })

class AddCourseView(ProfessorLoginRequiredMixin,CreateView):
    model = CourseList
    form_class = AddCourseForm
    template_name = "students/create.html"
    extra_context = {"prof":True}

    def form_valid(self, form):
        try:
            CourseList.objects.get(course_name=form.cleaned_data["course_name"])
            messages.error(self.request,"The course is already present.")
            return render(self.request,"students/create.html",{
                "form":form,
            })
        except CourseList.DoesNotExist:
            self.object = form.save()
        # adding created course to that professor's currently teaching list
        curr_prof = Professors.objects.get(prof=self.request.user)
        course = CourseList.objects.get(course_name=form.cleaned_data["course_name"])
        curr_prof.courses.add(course)
        self.kwargs["course_pk"]=course.pk
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse("add-students",kwargs={"pk":self.kwargs["course_pk"]})

@professor_required
def add_students(request,pk):
    course = CourseList.objects.get(pk=pk)
    if request.method=="POST":
        form = AddStudentsForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.course = course
            obj.marks = 0
            obj.sem=get_current_sem()
            try:
                Courses.objects.get(course=course,student=obj.student,sem=get_current_sem())
                messages.error(request,"The student is already enrolled in the course.")
                return render(request,"professors/add_students.html",{"form":AddStudentsForm(),"pk":pk})
            except Courses.DoesNotExist:
                obj.save()
            return redirect("prof-home")
    form = AddStudentsForm()
    return render(request,"professors/add_students.html",{
        "form":form,
        "pk":pk,
        "prof":True,
    })

@professor_required
def prof_course_detail(request,pk):
    try:
        Professors.objects.get(prof=request.user)
        prof=True
    except Professors.DoesNotExist:
        prof=False
    return course_detail(request,pk,prof)

class AnnouncementUpdateView(ProfessorLoginRequiredMixin,UpdateView):
    model = Announcements
    fields = ["title","msg","attachments"]
    template_name = "students/create.html"
    extra_context = {"prof":True}

    def get_form(self, form_class=None):
        form = super(AnnouncementUpdateView, self).get_form(form_class)
        form.fields['attachments'].required = False
        return form

    def get_object(self) :
        pk = self.kwargs.get("announce_pk")
        return get_object_or_404(Announcements,pk=pk)

    def get_success_url(self):
        return reverse("prof-coursedetail",kwargs={"pk":self.kwargs["pk"]})
    
class AnnouncementDeleteView(ProfessorLoginRequiredMixin,DeleteView):
    model = Announcements
    template_name = "professors/delete.html"
    extra_context = {"prof":True}

    def get_object(self) :
        pk = self.kwargs.get("announce_pk")
        return get_object_or_404(Announcements,pk=pk)

    def get_success_url(self):
        return reverse("prof-coursedetail",kwargs={"pk":self.kwargs["pk"]})
    
class ContentUpdateView(ProfessorLoginRequiredMixin,UpdateView):
    model = Content
    fields = ["title","attachments"]
    template_name = "students/create.html"
    extra_context = {"prof":True}

    def get_object(self) :
        pk = self.kwargs.get("content_pk")
        return get_object_or_404(Content,pk=pk)

    def get_success_url(self):
        return reverse("prof-coursedetail",kwargs={"pk":self.kwargs["pk"]})
    
class ContentDeleteView(ProfessorLoginRequiredMixin,DeleteView):
    model = Content
    template_name = "professors/delete.html"
    extra_context = {"prof":True}

    def get_object(self) :
        pk = self.kwargs.get("content_pk")
        return get_object_or_404(Content,pk=pk)

    def get_success_url(self):
        return reverse("prof-coursedetail",kwargs={"pk":self.kwargs["pk"]})

@professor_required 
def select_student_update_marks(request,pk,title):
    if request.method == "POST":
        form = UpdateStudentMarks(pk=pk,data=request.POST)
        if form.is_valid():
            selected_course = get_object_or_404(CourseList,pk=pk)
            selected_eval = Evals.objects.get(course = selected_course,
                                              title=title,
                                              student=form.cleaned_data["required_student"],
                                              sem=get_current_sem()
                                              )
            return redirect("update-marks",pk=pk,title=title,eval_pk=selected_eval.pk)

    form = UpdateStudentMarks(pk=pk)
    return render(request,"students/create.html",{
        "form":form,
        "prof":True,
    })

class MarkUpdateView(ProfessorLoginRequiredMixin,UpdateView):
    model = Evals
    fields = ["title","marks"]
    template_name = "students/create.html"
    extra_context = {"prof":True}

    def get_object(self) :
        pk = self.kwargs.get("eval_pk")
        return get_object_or_404(Evals,pk=pk)

    def get_success_url(self):
        return reverse("prof-coursedetail",kwargs={"pk":self.kwargs["pk"]})