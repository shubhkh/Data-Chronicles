import calendar as pycal
import json
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .forms import (
    ChallengeEntryForm,
    PersonalChallengeForm,
    ProfileForm,
    RegisterForm,
)
from .models import (
    Challenge,
    ChallengeEntry,
    PersonalChallenge,
    Profile,
    Task,
    TimerSession,
    UserChallenge,
)

KIND_META = {
    'stopwatch': ('Stopwatch', '#6f9aa8'),
    'countdown': ('Countdown', '#a394bd'),
    'pomodoro_focus': ('Pomodoro Focus', '#c48f8f'),
    'short_break': ('Short Break', '#8fa382'),
    'long_break': ('Long Break', '#8ba3c0'),
}


def home(request):
    today_stats = None
    if request.user.is_authenticated:
        today = timezone.localdate()
        today_secs = (
            request.user.timer_sessions
            .filter(finished_at__date=today, kind__in=STUDY_KINDS)
            .aggregate(s=Sum('seconds'))['s'] or 0
        )
        tasks_done = request.user.tasks.filter(
            is_done=True, completed_at__date=today,
        ).count()
        active_challenges = request.user.personal_challenges.filter(
            start_date__lte=today, end_date__gte=today,
        ).count()
        profile = getattr(request.user, 'timer_profile', None)
        goal = profile.daily_goal_minutes if profile else 60
        today_stats = {
            'focus': _fmt_minutes(today_secs),
            'tasks_done': tasks_done,
            'challenges': active_challenges,
            'goal_done': _fmt_minutes(today_secs),
            'goal_target': goal,
            'goal_pct': min(100, round(today_secs / 60 / goal * 100)),
        }
    return render(request, 'timers/home.html', {'today_stats': today_stats})


@ensure_csrf_cookie
def stopwatch(request):
    return render(request, 'timers/stopwatch.html')


@ensure_csrf_cookie
def countdown(request):
    return render(request, 'timers/countdown.html')


@ensure_csrf_cookie
def pomodoro(request):
    open_tasks = _owner_qs(Task, request).filter(is_done=False)
    return render(request, 'timers/pomodoro.html', {'open_tasks': open_tasks})


def _owner_qs(model, request):
    return model.objects.filter(
        user=request.user if request.user.is_authenticated else None
    )


@require_POST
def log_session(request):
    try:
        payload = json.loads(request.body)
        kind = payload['kind']
        seconds = int(payload['seconds'])
    except (KeyError, TypeError, ValueError):
        return JsonResponse({'ok': False}, status=400)
    if kind not in KIND_META or not 1 <= seconds <= 86400:
        return JsonResponse({'ok': False}, status=400)
    TimerSession.objects.create(
        kind=kind,
        seconds=seconds,
        task=str(payload.get('task', ''))[:80],
        user=request.user if request.user.is_authenticated else None,
    )
    return JsonResponse({'ok': True})


def register(request):
    if request.user.is_authenticated:
        return redirect('timers:profile')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.save())
        return redirect('timers:home')
    return render(request, 'timers/register.html', {'form': form})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('timers:profile')
    qs = request.user.timer_sessions.all()
    agg = qs.aggregate(s=Sum('seconds'), c=Count('id'))
    fav = qs.values('kind').annotate(s=Sum('seconds')).order_by('-s').first()
    ustats = {
        'sessions': agg['c'] or 0,
        'total': _fmt_minutes(agg['s'] or 0),
        'fav': KIND_META[fav['kind']][0] if fav else '—',
    }
    return render(request, 'timers/profile.html', {'form': form, 'ustats': ustats})


def tasks(request):
    qs = _owner_qs(Task, request)
    done = qs.filter(is_done=True).count()
    total = qs.count()
    return render(request, 'timers/tasks.html', {
        'tasks': qs,
        'done_count': done,
        'total_count': total,
        'progress': round(done / total * 100) if total else 0,
    })


@require_POST
def task_add(request):
    title = request.POST.get('title', '').strip()[:120]
    if title:
        Task.objects.create(
            title=title,
            user=request.user if request.user.is_authenticated else None,
        )
    return redirect('timers:tasks')


@require_POST
def task_toggle(request, pk):
    task = get_object_or_404(_owner_qs(Task, request), pk=pk)
    task.is_done = not task.is_done
    task.completed_at = timezone.now() if task.is_done else None
    task.save(update_fields=['is_done', 'completed_at'])
    return redirect('timers:tasks')


@require_POST
def task_delete(request, pk):
    get_object_or_404(_owner_qs(Task, request), pk=pk).delete()
    return redirect('timers:tasks')


CHALLENGE_SEED = [
    ('first-sprint', '\u26a1', 'First Sprint', 'Complete one focus session today.', 'focus_count_day', 1),
    ('warm-up', '\u2600\ufe0f', 'Warm Up', 'Log 30 minutes today across all timers.', 'minutes_day', 30),
    ('deep-work', '\U0001f9e0', 'Deep Work Day', 'Log 2 hours of focus time today.', 'focus_minutes_day', 120),
    ('pomodoro-pro', '\U0001f345', 'Pomodoro Pro', 'Finish 4 focus sessions today.', 'focus_count_day', 4),
    ('task-crusher', '\u2705', 'Task Crusher', 'Complete 5 to-dos in the last 7 days.', 'tasks_week', 5),
    ('on-a-roll', '\U0001f525', 'On a Roll', 'Use any timer 3 days in a row.', 'streak', 3),
    ('weekly-warrior', '\U0001f3c6', 'Weekly Warrior', 'Log 5 hours in the last 7 days.', 'minutes_week', 300),
    ('marathon', '\u26f0', 'Marathon Week', 'Log 10 hours in the last 7 days.', 'minutes_week', 600),
]


def _seed_challenges():
    for slug, icon, title, desc, gtype, gval in CHALLENGE_SEED:
        Challenge.objects.get_or_create(
            slug=slug,
            defaults={
                'icon': icon, 'title': title, 'description': desc,
                'goal_type': gtype, 'goal_value': gval,
            },
        )


def _challenge_progress(goal_type, goal_value, sessions, task_qs):
    """Return (current, target) progress for a challenge."""
    today = timezone.localdate()
    if goal_type == 'focus_minutes_day':
        secs = sessions.filter(kind='pomodoro_focus', finished_at__date=today) \
            .aggregate(s=Sum('seconds'))['s'] or 0
        return round(secs / 60), goal_value
    if goal_type == 'focus_count_day':
        return sessions.filter(kind='pomodoro_focus', finished_at__date=today).count(), goal_value
    if goal_type == 'minutes_day':
        secs = sessions.filter(finished_at__date=today).aggregate(s=Sum('seconds'))['s'] or 0
        return round(secs / 60), goal_value
    if goal_type == 'minutes_week':
        secs = sessions.filter(finished_at__date__gte=today - timedelta(days=6)) \
            .aggregate(s=Sum('seconds'))['s'] or 0
        return round(secs / 60), goal_value
    if goal_type == 'tasks_week':
        current = sum(
            1 for t in task_qs.filter(is_done=True)
            if timezone.localtime(t.completed_at or t.created_at).date() >= today - timedelta(days=6)
        )
        return current, goal_value
    if goal_type == 'streak':
        days = {
            r['day']
            for r in sessions.annotate(day=TruncDate('finished_at')).values('day')
        }
        streak = 0
        cursor = today if today in days else today - timedelta(days=1)
        while cursor in days:
            streak += 1
            cursor -= timedelta(days=1)
        return streak, goal_value
    return 0, goal_value


def _pc_status(pc, today):
    if today < pc.start_date:
        return 'upcoming'
    if today > pc.end_date:
        return 'finished'
    return 'active'


def challenges(request):
    _seed_challenges()
    user = request.user if request.user.is_authenticated else None

    personal = []
    if request.user.is_authenticated:
        today = timezone.localdate()
        for pc in request.user.personal_challenges.prefetch_related('entries'):
            elapsed = min(max(0, (today - pc.start_date).days + 1), pc.duration_days)
            done_days = sum(
                1 for e in pc.entries.all()
                if e.status == 'completed' and pc.start_date <= e.date <= pc.end_date
            )
            personal.append({
                'pc': pc,
                'done': done_days,
                'total': pc.duration_days,
                'pct': min(100, round(done_days / pc.duration_days * 100)),
                'status': _pc_status(pc, today),
            })

    sessions = TimerSession.objects.filter(user=user)
    sessions = TimerSession.objects.filter(user=user)
    task_qs = Task.objects.filter(user=user)
    accepted = {
        uc.challenge_id: uc
        for uc in UserChallenge.objects.filter(user=user).select_related('challenge')
    }

    active, available, done = [], [], []
    for ch in Challenge.objects.all():
        uc = accepted.get(ch.id)
        if uc is None:
            available.append(ch)
        elif uc.completed_at:
            done.append({'ch': ch, 'when': timezone.localtime(uc.completed_at).strftime('%d %b %Y')})
        else:
            current, target = _challenge_progress(ch.goal_type, ch.goal_value, sessions, task_qs)
            if current >= target:
                uc.completed_at = timezone.now()
                uc.save(update_fields=['completed_at'])
                done.append({'ch': ch, 'when': 'Just now'})
            else:
                active.append({
                    'ch': ch,
                    'current': current,
                    'target': target,
                    'pct': min(100, round(current / target * 100)),
                })
    return render(request, 'timers/challenges.html', {
        'active': active, 'available': available, 'done': done,
        'personal': personal,
    })


@login_required
def challenge_new(request):
    form = PersonalChallengeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        pc = form.save(commit=False)
        pc.user = request.user
        pc.save()
        return redirect('timers:challenge_detail', pk=pc.pk)
    return render(request, 'timers/challenge_form.html', {'form': form, 'editing': None})


@login_required
def challenge_edit(request, pk):
    pc = get_object_or_404(PersonalChallenge, pk=pk, user=request.user)
    form = PersonalChallengeForm(request.POST or None, instance=pc)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('timers:challenge_detail', pk=pc.pk)
    return render(request, 'timers/challenge_form.html', {'form': form, 'editing': pc})


@require_POST
@login_required
def challenge_delete(request, pk):
    get_object_or_404(PersonalChallenge, pk=pk, user=request.user).delete()
    return redirect('timers:challenges')


def _challenge_stats(pc, entries, today):
    end_view = min(today, pc.end_date)
    elapsed = (end_view - pc.start_date).days + 1 if end_view >= pc.start_date else 0
    counts = {'completed': 0, 'partial': 0, 'missed': 0}
    for e in entries.values():
        if e.status in counts and pc.start_date <= e.date <= pc.end_date:
            counts[e.status] += 1
    missed = counts['missed'] + max(0, elapsed - sum(counts.values()))
    consistency = round(counts['completed'] / elapsed * 100) if elapsed else 0

    cursor = end_view
    if entries.get(cursor) is None or entries[cursor].status != 'completed':
        cursor -= timedelta(days=1)
    streak = 0
    while cursor in entries and entries[cursor].status == 'completed':
        streak += 1
        cursor -= timedelta(days=1)

    return {
        'elapsed': elapsed,
        'completed': counts['completed'],
        'partial': counts['partial'],
        'missed': missed,
        'consistency': consistency,
        'streak': streak,
        'finished': today > pc.end_date,
    }


def _challenge_calendar(pc, entries, today):
    months = []
    mcur = pc.start_date.replace(day=1)
    cal = pycal.Calendar(firstweekday=0)
    while mcur <= pc.end_date:
        weeks = []
        for week in cal.monthdayscalendar(mcur.year, mcur.month):
            row = []
            for num in week:
                if num == 0:
                    row.append(None)
                    continue
                d = date(mcur.year, mcur.month, num)
                if d < pc.start_date or d > pc.end_date:
                    row.append(None)
                    continue
                e = entries.get(d)
                row.append({
                    'day': num,
                    'iso': d.isoformat(),
                    'status': e.status if e else ('future' if d > today else 'pending'),
                    'today': d == today,
                    'loggable': d <= today,
                })
            weeks.append(row)
        months.append({'label': mcur.strftime('%B %Y'), 'weeks': weeks})
        mcur = (mcur + timedelta(days=32)).replace(day=1)
    return months


@login_required
def challenge_detail(request, pk):
    pc = get_object_or_404(PersonalChallenge, pk=pk, user=request.user)
    today = timezone.localdate()
    entries = {e.date: e for e in pc.entries.all()}
    stats = _challenge_stats(pc, entries, today)

    return render(request, 'timers/challenge_detail.html', {
        'pc': pc,
        'stats': stats,
        'months': _challenge_calendar(pc, entries, today),
        'recent_entries': pc.entries.all()[:10],
        'improvements': [e.improvements for e in pc.entries.exclude(improvements='')[:5]],
        'can_log_today': pc.start_date <= today <= pc.end_date and today not in entries,
        'today_iso': today.isoformat(),
        'status': _pc_status(pc, today),
    })


@login_required
def challenge_entry(request, pk, day):
    pc = get_object_or_404(PersonalChallenge, pk=pk, user=request.user)
    try:
        d = date.fromisoformat(day)
    except ValueError:
        raise Http404
    today = timezone.localdate()
    if not (pc.start_date <= d <= pc.end_date) or d > today:
        raise Http404
    entry = pc.entries.filter(date=d).first()
    form = ChallengeEntryForm(request.POST or None, instance=entry)
    if request.method == 'POST' and form.is_valid():
        e = form.save(commit=False)
        e.challenge = pc
        e.date = d
        e.save()
        return redirect('timers:challenge_detail', pk=pk)
    return render(request, 'timers/challenge_entry.html', {
        'pc': pc, 'form': form, 'day': d, 'entry': entry,
    })


@require_POST
def challenge_accept(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk)
    user = request.user if request.user.is_authenticated else None
    UserChallenge.objects.get_or_create(
        user=user, challenge=challenge,
        defaults={'accepted_at': timezone.now()},
    )
    return redirect('timers:challenges')


def _fmt_minutes(seconds):
    minutes = round(seconds / 60)
    if minutes <= 0:
        return '0m'
    h, m = divmod(minutes, 60)
    return f'{h}h {m}m' if h else f'{m}m'


RANGE_DAYS = {'7': 7, '30': 30, '90': 90}

# Kinds that count as productive study/work time; breaks never count.
STUDY_KINDS = {'stopwatch', 'countdown', 'pomodoro_focus'}
BREAK_KINDS = {'short_break', 'long_break'}


def report(request):
    today = timezone.localdate()

    range_param = request.GET.get('range', '30')
    kind_param = request.GET.get('kind', 'all')
    if kind_param not in KIND_META:
        kind_param = 'all'

    owner_qs = TimerSession.objects.filter(
        user=request.user if request.user.is_authenticated else None
    )
    qs = owner_qs if kind_param == 'all' else owner_qs.filter(kind=kind_param)

    if range_param == 'all':
        first = qs.order_by('finished_at').first()
        span = (today - timezone.localtime(first.finished_at).date()).days + 1 if first else 30
        n_days = min(span, 365)
        sessions = qs
        start_date = None
    else:
        if range_param not in RANGE_DAYS:
            range_param = '30'
        n_days = RANGE_DAYS[range_param]
        start_date = today - timedelta(days=n_days - 1)
        sessions = qs.filter(finished_at__date__gte=start_date)

    has_any = owner_qs.exists()
    has_data = sessions.exists()

    # Study-time view: when unfiltered, productive kinds only; when a specific
    # kind is selected, show that kind as-is.
    study_qs = sessions if kind_param != 'all' else sessions.filter(kind__in=STUDY_KINDS)

    goal_minutes = None
    if request.user.is_authenticated:
        profile = getattr(request.user, 'timer_profile', None)
        goal_minutes = profile.daily_goal_minutes if profile else 60

    stats = {'today': '0m', 'week': '0m', 'total': '0m', 'count': 0, 'avg': '0m', 'goal': None}
    insights = []
    donut = {'labels': [], 'data': [], 'colors': []}
    donut_title = 'Where your focus went' if kind_param != 'all' else 'Where your time went'
    bar = {'labels': [], 'data': [], 'goal': goal_minutes or 0}
    area = {'labels': [], 'data': []}
    sess_chart = {'labels': [], 'data': []}
    focus_break = {'labels': [], 'focus': [], 'breaks': []}
    recent = []

    if has_data:
        total_secs = sessions.aggregate(s=Sum('seconds'))['s'] or 0
        study_secs = study_qs.aggregate(s=Sum('seconds'))['s'] or 0
        today_secs = study_qs.filter(finished_at__date=today).aggregate(s=Sum('seconds'))['s'] or 0
        week_secs = study_qs.filter(finished_at__date__gte=today - timedelta(days=6)).aggregate(s=Sum('seconds'))['s'] or 0

        stats['count'] = sessions.count()
        stats['total'] = _fmt_minutes(study_secs)
        stats['today'] = _fmt_minutes(today_secs)
        stats['week'] = _fmt_minutes(week_secs)
        stats['avg'] = _fmt_minutes(round(study_secs / n_days))
        if goal_minutes:
            stats['goal'] = {
                'done': _fmt_minutes(today_secs),
                'target': f'{goal_minutes}m',
                'pct': min(100, round(today_secs / 60 / goal_minutes * 100)),
            }

        # Per-day aggregates on the study-time basis
        daily = {
            r['day']: (r['s'] or 0, r['c'])
            for r in study_qs.annotate(day=TruncDate('finished_at'))
            .values('day').annotate(s=Sum('seconds'), c=Count('id'))
        }
        daily_all = {
            r['day']: r['c']
            for r in sessions.annotate(day=TruncDate('finished_at'))
            .values('day').annotate(c=Count('id'))
        }
        days = [today - timedelta(days=n_days - 1 - i) for i in range(n_days)]
        fmt = '%d %b'

        bar['labels'] = [d.strftime(fmt) for d in days]
        bar['data'] = [round(daily.get(d, (0, 0))[0] / 60, 1) for d in days]
        sess_chart['labels'] = bar['labels']
        sess_chart['data'] = [daily_all.get(d, 0) for d in days]

        cumulative = 0
        for d in days:
            cumulative += daily.get(d, (0, 0))[0]
            area['data'].append(round(cumulative / 60, 1))
        area['labels'] = bar['labels']

        # Focus vs break totals for the whole period (all kinds view only)
        if kind_param == 'all':
            focus_break['focus'] = round(study_secs / 60, 1)
            focus_break['breaks'] = round(
                (sessions.filter(kind__in=BREAK_KINDS).aggregate(s=Sum('seconds'))['s'] or 0) / 60, 1
            )

        # Donut: by activity when unfiltered, by task when a kind is selected
        donut['total'] = _fmt_minutes(total_secs)
        donut['single'] = None
        if kind_param == 'all':
            kind_totals = {r['kind']: r['s'] for r in sessions.values('kind').annotate(s=Sum('seconds'))}
            donut['slugs'] = []
            for kind, (label, color) in KIND_META.items():
                if kind_totals.get(kind):
                    donut['labels'].append(label)
                    donut['data'].append(round(kind_totals[kind] / 60, 1))
                    donut['colors'].append(color)
                    donut['slugs'].append(kind)
        else:
            task_rows = (sessions.exclude(task='')
                         .values('task').annotate(s=Sum('seconds')).order_by('-s')[:8])
            other = sessions.filter(task='').aggregate(s=Sum('seconds'))['s'] or 0
            palette = ['#c48f8f', '#6f9aa8', '#a394bd', '#8fa382', '#8ba3c0']
            for i, r in enumerate(task_rows):
                donut['labels'].append(r['task'])
                donut['data'].append(round(r['s'] / 60, 1))
                donut['colors'].append(palette[i % len(palette)])
            if other:
                donut['labels'].append('Untitled')
                donut['data'].append(round(other / 60, 1))
                donut['colors'].append('#c9c2b2')

        if len(donut['labels']) == 1:
            donut['single'] = donut['labels'][0]

        # Insights: icon, title, value, explanation
        if daily:
            best = max(daily.items(), key=lambda kv: kv[1][0])
            insights.append({
                'icon': '🏆', 'title': 'Most productive day',
                'value': f"{best[0].strftime(fmt)} · {_fmt_minutes(best[1][0])}",
                'sub': 'your highest single-day total',
            })

        longest = study_qs.order_by('-seconds').first()
        if longest:
            label = KIND_META[longest.kind][0]
            if longest.task:
                label += f' · {longest.task}'
            insights.append({
                'icon': '⏱', 'title': 'Longest focus session',
                'value': f"{_fmt_minutes(longest.seconds)}",
                'sub': f"{label} · {timezone.localtime(longest.finished_at).strftime(fmt)}",
            })

        insights.append({
            'icon': '≈', 'title': 'Avg daily focus',
            'value': _fmt_minutes(round(study_secs / n_days)),
            'sub': f'across {n_days} days',
        })

        # Streak: consecutive days with study activity (grace for today)
        day_set = set(daily.keys())
        cursor = today if today in day_set else today - timedelta(days=1)
        streak = 0
        while cursor in day_set:
            streak += 1
            cursor -= timedelta(days=1)
        insights.append({
            'icon': '🔥', 'title': 'Current streak',
            'value': f'{streak} day' + ('s' if streak != 1 else ''),
            'sub': 'study days in a row',
        })

        if goal_minutes:
            met = sum(1 for secs, _c in daily.values() if secs >= goal_minutes * 60)
            insights.append({
                'icon': '🎯', 'title': 'Goal completion',
                'value': f'{met} / {n_days}',
                'sub': f'days reached {goal_minutes}m+',
            })

        recent = [{
            'when': timezone.localtime(s.finished_at).strftime('%d %b · %I:%M %p'),
            'kind': KIND_META[s.kind][0],
            'task': s.task or '—',
            'dur': _fmt_minutes(s.seconds) if s.seconds >= 60 else f'{s.seconds}s',
        } for s in sessions[:10]]

    # Completed to-do history (respects range, not the activity kind filter)
    done_entries = []
    for t in _owner_qs(Task, request).filter(is_done=True):
        eff = t.completed_at or t.created_at
        if start_date is None or timezone.localtime(eff).date() >= start_date:
            done_entries.append((eff, t.title))
    done_tasks = [
        {
            'title': title,
            'when': timezone.localtime(eff).strftime('%d %b %Y · %I:%M %p'),
        }
        for eff, title in sorted(done_entries, key=lambda e: e[0], reverse=True)[:15]
    ]

    return render(request, 'timers/report.html', {
        'has_any': has_any,
        'has_data': has_data,
        'stats': stats,
        'insights': insights,
        'recent': recent,
        'done_tasks': done_tasks,
        'range': range_param,
        'kind': kind_param,
        'kind_label': KIND_META[kind_param][0] if kind_param != 'all' else 'study time',
        'donut_title': donut_title,
        'show_focus_break': kind_param == 'all',
        'report_data': {
            'donut': donut, 'bar': bar, 'area': area,
            'sessions': sess_chart, 'focus_break': focus_break,
        },
    })


def _session_rows(qs):
    return [{
        'id': s.pk,
        'when': timezone.localtime(s.finished_at).strftime('%d %b %Y · %I:%M %p'),
        'kind': KIND_META[s.kind][0],
        'task': s.task or '—',
        'dur': _fmt_minutes(s.seconds) if s.seconds >= 60 else f'{s.seconds}s',
        'secs': s.seconds,
    } for s in qs]


def sessions_history(request):
    qs = _owner_qs(TimerSession, request)
    kind = request.GET.get('kind', 'all')
    if kind in KIND_META:
        qs = qs.filter(kind=kind)
    else:
        kind = 'all'

    sort = request.GET.get('sort', 'date')
    order = request.GET.get('dir', 'desc')
    field = 'finished_at' if sort == 'date' else 'seconds'
    qs = qs.order_by(('-' if order == 'desc' else '') + field)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'timers/sessions.html', {
        'rows': _session_rows(page_obj),
        'page_obj': page_obj,
        'kind': kind,
        'sort': sort,
        'dir': order,
        'kinds': KIND_META,
    })
