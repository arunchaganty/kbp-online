from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Submission, SubmissionUser, SubmissionState

admin.site.register(User, UserAdmin)

def rescore_submission(modeladmin, request, queryset):
    for row in queryset:
        print(row)
rescore_submission.short_description = "Rescore submission using the latest data."

class SubmissionUserInline(admin.TabularInline):
    model = SubmissionUser

class SubmissionStateInline(admin.TabularInline):
    model = SubmissionState

class SubmissionAdmin(admin.ModelAdmin):
    fields = (('name', 'corpus_tag'), 'details')
    readonly_fields = ('name', 'corpus_tag', 'details')
    inlines = [
        SubmissionUserInline,
        SubmissionStateInline,
        ]
    actions = [rescore_submission]

    def user(self, obj):
        return SubmissionUser.objects.get(submission=obj).user

    def status(self, obj):
        return SubmissionState.objects.get(submission=obj).status

    list_display = ('name', 'corpus_tag', 'user', 'status')



admin.site.register(Submission, SubmissionAdmin)
