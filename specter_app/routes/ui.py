from flask import Blueprint, render_template_string, abort
from ..utils.ui_templates import UI_BASE, DASHBOARD_BODY, ADMIN_BODY, WATCHLIST_BODY, PROCESS_BODY
from ..utils.helpers import CNJ_REGEX

ui_bp = Blueprint("ui", __name__, url_prefix="/ui")

@ui_bp.get("/")
def ui_home():
    from flask import redirect
    return redirect("/ui/dashboard")

@ui_bp.get("/dashboard")
def dashboard():
    return render_template_string(UI_BASE, body=DASHBOARD_BODY)

@ui_bp.get("/admin")
def admin():
    return render_template_string(UI_BASE, body=ADMIN_BODY)

@ui_bp.get("/watchlist")
def watchlist():
    return render_template_string(UI_BASE, body=WATCHLIST_BODY)

@ui_bp.get("/processo/<path:cnj>")
def processo_detail(cnj: str):
    if not CNJ_REGEX.fullmatch(cnj): abort(404)
    return render_template_string(UI_BASE, body=PROCESS_BODY.replace("{{ cnj }}", cnj))

@ui_bp.get("/docs")
def documentation():
    doc_html = """
    <div class="card p-4">
        <h1>Documentação do Specter</h1>
        <p>Este sistema é um monitor jurídico modularizado.</p>
        <h3>API V2 (Escavador)</h3>
        <ul>
            <li><b>Watchlist:</b> Gerenciamento de documentos monitorados.</li>
            <li><b>Processos:</b> Descoberta e vinculação de CNJs.</li>
            <li><b>Movimentações:</b> Sincronização de eventos em tempo real.</li>
        </ul>
    </div>
    """
    return render_template_string(UI_BASE, body=doc_html)
