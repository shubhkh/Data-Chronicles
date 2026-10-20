(function () {
    'use strict';

    window.logSession = function (kind, seconds, task) {
        var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        fetch('/api/sessions/', {
            method: 'POST',
            keepalive: true,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': m ? m[1] : '',
            },
            body: JSON.stringify({
                kind: kind,
                seconds: Math.round(seconds),
                task: task || '',
            }),
        }).then(function (r) {
            if (r.ok) document.dispatchEvent(new CustomEvent('sessionsaved'));
        }).catch(function () { /* logging is best-effort */ });
    };
})();
