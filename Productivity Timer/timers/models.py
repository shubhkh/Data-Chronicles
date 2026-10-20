from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class TimerSession(models.Model):
    KIND_CHOICES = [
        ('stopwatch', 'Stopwatch'),
        ('countdown', 'Countdown'),
        ('pomodoro_focus', 'Pomodoro Focus'),
        ('short_break', 'Short Break'),
        ('long_break', 'Long Break'),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    user = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='timer_sessions',
    )
    seconds = models.PositiveIntegerField()
    task = models.CharField(max_length=80, blank=True)
    finished_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-finished_at']
        indexes = [models.Index(fields=['user', 'finished_at'])]

    def __str__(self):
        return f'{self.get_kind_display()} · {self.seconds}s'


class Task(models.Model):
    user = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='tasks',
    )
    title = models.CharField(max_length=120)
    is_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['is_done', '-created_at']

    def __str__(self):
        return self.title


class Challenge(models.Model):
    GOAL_TYPES = [
        ('focus_minutes_day', 'Focus minutes today'),
        ('focus_count_day', 'Focus sessions today'),
        ('minutes_day', 'Timer minutes today'),
        ('minutes_week', 'Timer minutes this week'),
        ('tasks_week', 'To-dos done this week'),
        ('streak', 'Day streak'),
    ]

    slug = models.SlugField(max_length=40, unique=True)
    icon = models.CharField(max_length=8, default='◆')
    title = models.CharField(max_length=80)
    description = models.CharField(max_length=200)
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPES)
    goal_value = models.PositiveIntegerField()

    def __str__(self):
        return self.title


class UserChallenge(models.Model):
    user = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.CASCADE, related_name='challenges',
    )
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    accepted_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-accepted_at']


class PersonalChallenge(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='personal_challenges',
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    goal = models.CharField(max_length=200, blank=True)
    daily_target = models.CharField(max_length=120, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return self.name


class ChallengeEntry(models.Model):
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('partial', 'Partially completed'),
        ('missed', 'Missed'),
    ]

    challenge = models.ForeignKey(
        PersonalChallenge, on_delete=models.CASCADE, related_name='entries',
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    did = models.TextField(blank=True)
    learned = models.TextField(blank=True)
    difficulties = models.TextField(blank=True)
    improvements = models.TextField(blank=True)
    plan_next = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('challenge', 'date')
        ordering = ['-date']

    def __str__(self):
        return f'{self.challenge.name} · {self.date}'


class Profile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='timer_profile',
    )
    daily_goal_minutes = models.PositiveIntegerField(default=60)

    def __str__(self):
        return f'{self.user.username} profile'
