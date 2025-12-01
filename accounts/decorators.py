from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def admin_required(view_func):
    """
    Permette l'accesso solo agli utenti con role='admin'.
    Richiede che l'utente sia autenticato.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        # Controllo ruolo amministratore (come definito nel tuo modello)
        if getattr(user, "role", None) != "admin":
            return HttpResponseForbidden("Non hai i permessi per accedere a questa area.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view
