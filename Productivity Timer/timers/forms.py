from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import ChallengeEntry, PersonalChallenge, Profile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'email')


class ProfileForm(forms.ModelForm):
    daily_goal_minutes = forms.IntegerField(
        min_value=5, max_value=1440, label='Daily goal (minutes)',
        help_text='Used for the goal line and goal stats on your report.',
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        labels = {'first_name': 'First name', 'last_name': 'Last name'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, 'timer_profile', None)
        if profile:
            self.fields['daily_goal_minutes'].initial = profile.daily_goal_minutes

    def save(self, commit=True):
        user = super().save(commit=commit)
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.daily_goal_minutes = self.cleaned_data['daily_goal_minutes']
        if commit:
            profile.save()
        return user


class PersonalChallengeForm(forms.ModelForm):
    class Meta:
        model = PersonalChallenge
        fields = ('name', 'description', 'goal', 'daily_target', 'start_date', 'end_date')
        labels = {
            'daily_target': 'Daily target',
            'start_date': 'Start date',
            'end_date': 'End date',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Why this challenge?'}),
            'goal': forms.TextInput(attrs={'placeholder': 'e.g. Build a daily reading habit'}),
            'daily_target': forms.TextInput(attrs={'placeholder': 'e.g. Read 20 pages'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'id': 'pc-start'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'id': 'pc-end'}),
        }

    def clean(self):
        data = super().clean()
        start, end = data.get('start_date'), data.get('end_date')
        if start and end:
            if end < start:
                self.add_error('end_date', 'End date must be on or after the start date.')
            elif (end - start).days > 364:
                self.add_error('end_date', 'Challenges can be at most 365 days long.')
        return data


class ChallengeEntryForm(forms.ModelForm):
    class Meta:
        model = ChallengeEntry
        fields = ('status', 'did', 'learned', 'difficulties', 'improvements', 'plan_next')
        labels = {
            'status': 'How did today go?',
            'did': 'What did you do today?',
            'learned': 'What did you experience or learn?',
            'difficulties': 'What difficulties did you face?',
            'improvements': 'What improvements did you notice?',
            'plan_next': 'What will you do better tomorrow?',
        }
        widgets = {
            'status': forms.RadioSelect(),
            'did': forms.Textarea(attrs={'rows': 2}),
            'learned': forms.Textarea(attrs={'rows': 2}),
            'difficulties': forms.Textarea(attrs={'rows': 2}),
            'improvements': forms.Textarea(attrs={'rows': 2}),
            'plan_next': forms.Textarea(attrs={'rows': 2}),
        }
