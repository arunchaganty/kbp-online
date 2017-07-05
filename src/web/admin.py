from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms

from kbpo import api
from kbpo import db
from kbpo import questions
from kbpo import turk

from .models import User, Submission, SubmissionUser, SubmissionState
from .models import EvaluationBatch, EvaluationQuestion, MturkBatch, MturkHit, MturkAssignment
from . import tasks

admin.site.register(User, UserAdmin)

# ==== Submission
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
        tasks.sample_submission.delay(row.id, n_samples=500)
resample_submission.short_description = "Resample submission (500 samples) (warning will create a new sample that may be turked)."

def resample_submission_medium(_, __, queryset):
    for row in queryset:
        row.state.status = 'pending-sampling'
        row.state.message = ""
        row.state.save()
        tasks.sample_submission.delay(row.id, n_samples=100)
resample_submission_medium.short_description = "Resample submission a medium batch (100 samples) (warning will create a new sample that may be turked)."

def resample_submission_tiny(_, __, queryset):
    for row in queryset:
        row.state.status = 'pending-sampling'
        row.state.message = ""
        row.state.save()
        tasks.sample_submission.delay(row.id, n_samples=5)
resample_submission_tiny.short_description = "Resample submission a tiny batch (5 samples) (warning will create a new sample that may be turked)."


def returk_submission(_, __, queryset):
    for row in queryset:
        # get the latest sample batch
        batches = api.get_submission_sample_batches(row.id)
        if len(batches) == 0:
            row.state.status = 'error'
            row.state.message = "Could not turk submission because there are no samples for it!"
            row.state.save()
        else:
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

class SubmissionStateInlineForm(forms.ModelForm):
    class Meta:
        model = SubmissionState
        fields = ('status', 'message')
        widgets={'status': forms.Select(dict(SubmissionState.CHOICES))}

class SubmissionStateInline(admin.TabularInline):
    model = SubmissionState
    fields = ('status', 'message')
    form = SubmissionStateInlineForm

class SubmissionAdmin(admin.ModelAdmin):
    fields = (('name', 'corpus_tag'), 'details')
    readonly_fields = ('name', 'corpus_tag', 'details')
    inlines = [
        SubmissionUserInline,
        SubmissionStateInline,
        ]
    actions = [reupload_submission, resample_submission, resample_submission_medium, resample_submission_tiny, returk_submission, rescore_submission]

    def _user(self, obj):
        return obj.user.user

    def _status(self, obj):
        return obj.state.status

    list_display = ('name', 'corpus_tag', 'active', '_user', '_status')
admin.site.register(Submission, SubmissionAdmin)

# ==== Evaluation
def revoke_evaluation_batch(_, __, queryset):
    mturk_conn = turk.connect()
    for row in queryset:
        questions.revoke_question_batch(row.id, mturk_conn=mturk_conn)
revoke_evaluation_batch.short_description = "Revoke"

class EvaluationQuestionInlineForm(forms.ModelForm):
    class Meta:
        model = EvaluationQuestion
        fields = ('state',)
        widgets = {'state': forms.Select(dict(EvaluationQuestion.CHOICES))}

class EvaluationQuestionInline(admin.TabularInline):
    model = EvaluationQuestion
    readonly_fields = ('id', 'params',)
    fields = (('id', 'params'), ('state', 'message'))
    form = EvaluationQuestionInlineForm

class EvaluationBatchAdmin(admin.ModelAdmin):
    readonly_fields = ('batch_type', 'corpus_tag', 'created',)
    fields = (('batch_type', 'corpus_tag', 'created',), 'description')

    inlines = [
        EvaluationQuestionInline,
        ]
    actions = [revoke_evaluation_batch,]

    # TODO: Render status better
    def _status(self, obj):
        return api.get_evaluation_batch_status(obj.id)

    list_display = ('created', 'description', 'batch_type', 'corpus_tag', '_status',)
admin.site.register(EvaluationBatch, EvaluationBatchAdmin)

def revoke_evaluation_question(_, __, queryset):
    mturk_conn = turk.connect()
    questions.revoke_question(row.batch_id, row.id, mturk_conn=mturk_conn)
revoke_evaluation_question.short_description = "Revoke"

class EvaluationQuestionAdmin(admin.ModelAdmin):
    model = EvaluationQuestion
    readonly_fields = ('id', 'params',)
    fields = (('id', 'params',), ('state', 'message'))

    form = EvaluationQuestionInlineForm
    list_display = ('id', 'batch', 'state', 'message',)
    list_filter = ('batch', 'state')
    actions = [revoke_evaluation_question,]
admin.site.register(EvaluationQuestion, EvaluationQuestionAdmin)

def revoke_mturk_batch(_, __, queryset):
    conn = turk.connect()
    for row in queryset:
        turk.revoke_batch(conn, row.id)
revoke_mturk_batch.short_description = "Revoke"

def handle_mturk_batch_payments(_, __, queryset):
    conn = turk.connect()
    for row in queryset:
        turk.mturk_batch_payments(conn, row.id)
revoke_mturk_batch.short_description = "Pay"

def process_mturk_batch(_, __, queryset):
    for row in queryset:
        tasks.process_mturk_batch.delay(row.id)

process_mturk_batch.short_description = "Reprocess"

class MTurkBatchAdmin(admin.ModelAdmin):
    list_display = ('created', 'description', '_status')

    # TODO display nicely
    def _status(self, obj):
        return api.get_mturk_batch_status(obj.id)
    actions = [revoke_mturk_batch, handle_mturk_batch_payments, process_mturk_batch]
admin.site.register(MturkBatch, MTurkBatchAdmin)

def revoke_mturk_hit(_, __, queryset):
    conn = turk.connect()
    for row in queryset:
        turk.revoke_hit(conn, row.id)
revoke_mturk_hit.short_description = "Revoke"

def increment_assignments(_, __, queryset):
    conn = turk.connect()
    for row in queryset:
        turk.increment_assignments(conn, row.id)
increment_assignments.short_description = "Increment assignments"

class MTurkHitAdmin(admin.ModelAdmin):
    list_display = ('id', 'batch', 'question_batch', 'state', 'message')
    list_filter = ('state', 'batch_id')

    actions = [revoke_mturk_hit, increment_assignments]
admin.site.register(MturkHit, MTurkHitAdmin)

class MTurkAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'worker_id', 'worker_time', 'hit_id', 'verified', 'state', 'message')
    list_filter = ('state', 'batch_id')

    # TODO: Approve or Reject.
admin.site.register(MturkAssignment, MTurkAssignmentAdmin)
