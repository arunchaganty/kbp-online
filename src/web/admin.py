from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Submission, SubmissionUser, SubmissionState
from web.tasks import score_submission

admin.site.register(User, UserAdmin)

def rescore_submission(_, __, queryset):
    for row in queryset:
        row.state.status = 'pending-scoring'
        row.state.save()
        score_submission.delay(row.id)
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

    def _user(self, obj):
        return obj.user.user

    def _status(self, obj):
        return obj.state.status

    list_display = ('name', 'corpus_tag', '_user', '_status')
admin.site.register(Submission, SubmissionAdmin)
