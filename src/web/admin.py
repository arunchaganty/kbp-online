from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Submission, SubmissionUser, SubmissionState
from .models import EvaluationBatch
from . import tasks

admin.site.register(User, UserAdmin)

def reupload_submission(_, __, queryset):
    for row in queryset:
        row.state.status = 'pending-upload'
        row.state.message = ""
        row.state.save()
        tasks.process_submission.delay(row.id)
reupload_submission.short_description = "Reupload submission."

def resample_submission(_, __, queryset):
    for row in queryset:
        row.state.status = 'pending-sampling'
        row.state.message = ""
        row.state.save()
        tasks.sample_submission.delay(row.id)
resample_submission.short_description = "Resample submission (warning will create a new sample that may be turked)."

def returk_submission(_, __, queryset):
    for row in queryset:
        row.state.status = 'pending-turking'
        row.state.message = ""
        row.state.save()
        tasks.turk_submission.delay(row.id)
returk_submission.short_description = "Returk submission (warning may cost money)."

def rescore_submission(_, __, queryset):
    for row in queryset:
        row.state.status = 'pending-scoring'
        row.state.message = ""
        row.state.save()
        tasks.score_submission.delay(row.id)
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
    actions = [reupload_submission, resample_submission, returk_submission, rescore_submission]

    def _user(self, obj):
        return obj.user.user

    def _status(self, obj):
        return obj.state.status

    list_display = ('name', 'corpus_tag', '_user', '_status')
admin.site.register(Submission, SubmissionAdmin)

class EvaluationBatchAdmin(admin.ModelAdmin):
    pass
admin.site.register(EvaluationBatch, EvaluationBatchAdmin)
