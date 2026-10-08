from flask import g, request

# No inline scripts or styles are used by the templates, so a strict policy works.
CSP = (
    "default-src 'self'; "
    "img-src 'self' data:; "
    "script-src 'self'; "
    "style-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


def init_app(app):
    @app.after_request
    def add_security_headers(response):
        headers = response.headers
        headers.setdefault("Content-Security-Policy", CSP)
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        # "same-origin" rather than "no-referrer": Flask-WTF checks the
        # Referer header on HTTPS form posts, so same-site requests must send it.
        headers.setdefault("Referrer-Policy", "same-origin")
        headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        # Keep evidence pages and downloads out of the browser cache.
        if request.endpoint != "static" and g.get("user") is not None:
            headers["Cache-Control"] = "no-store"
        # Only meaningful over HTTPS, so tie it to the secure-cookie setting.
        if app.config.get("SESSION_COOKIE_SECURE"):
            headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response