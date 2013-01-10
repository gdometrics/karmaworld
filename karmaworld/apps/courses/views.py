from django.views.generic import DetailView
from karmaworld.apps.courses.models import Course

class CourseDetailView(DetailView):
    """ Class-based view for the course html page """

    # name passed to template
    context_object_name = u"course"
    model = Course

