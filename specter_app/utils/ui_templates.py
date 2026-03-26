UI_BASE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Specter Monitor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root { --bg: #0f111a; --card: #1a1d2e; --accent: #4f46e5; --text: #e2e8f0; --muted: #94a3b8; }
        body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; }
        .navbar { background: var(--card); border-bottom: 1px solid rgba(255,255,255,.05); }
        .card { background: var(--card); border: 1px solid rgba(255,255,255,.05); color: var(--text); }
        .muted { color: var(--muted); }
        .mono { font-family: 'JetBrains Mono', monospace; }
        .btn-primary { background: var(--accent); border: none; }
        .divider { border-color: rgba(255,255,255,.1); }
        .nav-link { color: var(--muted); }
        .nav-link.active { color: #fff; font-weight: 600; }
        .badge-soft { background: rgba(79, 70, 229, 0.1); color: #818cf8; border: 1px solid rgba(79,70,229,.2); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark mb-4">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/ui/dashboard"><i class="fas fa-ghost me-2"></i>SPECTER</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navMain">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navMain">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item"><a class="nav-link" id="nav-dash" href="/ui/dashboard">Dashboard</a></li>
                    <li class="nav-item"><a class="nav-link" id="nav-wl" href="/ui/watchlist">Watchlist</a></li>
                    <li class="nav-item"><a class="nav-link" id="nav-doc" href="/ui/docs">Documentação</a></li>
                </ul>
                <div class="d-flex align-items-center gap-3">
                    <form class="d-flex" onsubmit="event.preventDefault(); window.location.href='/ui/processo/'+document.getElementById('q-cnj').value;">
                        <input class="form-control form-control-sm bg-dark text-light border-secondary" type="search" id="q-cnj" placeholder="Buscar CNJ..." aria-label="Search">
                    </form>
                    <a href="/ui/admin" class="btn btn-outline-secondary btn-sm"><i class="fas fa-cog"></i></a>
                </div>
            </div>
        </div>
    </nav>
    <div class="container">
        {{ body|safe }}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Active link helper
        const path = window.location.pathname;
        if(path.includes('dashboard')) document.getElementById('nav-dash')?.classList.add('active');
        if(path.includes('watchlist')) document.getElementById('nav-wl')?.classList.add('active');
        if(path.includes('docs')) document.getElementById('nav-doc')?.classList.add('active');
    </script>
</body>
</html>
"""

DASHBOARD_BODY = """
<div class="row g-3 mb-4">
    <div class="col-md-3">
        <div class="card p-3 text-center">
            <div class="muted small mb-1">Watchlist</div>
            <div class="h3 mb-0 fw-bold" id="m-docs">-</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card p-3 text-center">
            <div class="muted small mb-1">Processos</div>
            <div class="h3 mb-0 fw-bold" id="m-procs">-</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card p-3 text-center text-info">
            <div class="muted small mb-1">Eventos</div>
            <div class="h3 mb-0 fw-bold" id="m-events">-</div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card p-3 text-center text-warning">
            <div class="muted small mb-1">Alertas</div>
            <div class="h3 mb-0 fw-bold" id="m-alerts">-</div>
        </div>
    </div>
</div>

<div class="row g-3">
    <div class="col-md-8">
        <div class="card p-3 mb-3">
            <div class="h5 mb-3">Últimas Movimentações Relevantes</div>
            <div id="alerts-list" class="small">
                <div class="text-center py-4 muted"><span class="spinner-border spinner-border-sm me-2"></span>Carregando...</div>
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="card p-3 mb-3">
            <div class="h6 mb-3">Top Processos (Alertas)</div>
            <div id="top-cnjs" class="small"></div>
        </div>
        <div class="card p-3">
            <div class="h6 mb-3">Custos Estimados</div>
            <div class="d-flex justify-content-between mb-1">
                <span class="muted small">Hoje:</span>
                <span class="fw-bold" id="c-today">R$ 0,00</span>
            </div>
            <div class="d-flex justify-content-between">
                <span class="muted small">Mês:</span>
                <span class="fw-bold" id="c-month">R$ 0,00</span>
            </div>
        </div>
    </div>
</div>

<script>
async function loadMetrics() {
    const r = await fetch('/ui/api/dashboard/metrics');
    const j = await r.json();
    if(j.ok) {
        document.getElementById('m-docs').textContent = j.docs;
        document.getElementById('m-procs').textContent = j.processos;
        document.getElementById('m-events').textContent = j.movs;
        document.getElementById('m-alerts').textContent = j.alertas;
        document.getElementById('c-today').textContent = 'R$ ' + j.cost_today_brl.toLocaleString('pt-BR', {minimumFractionDigits:2});
        document.getElementById('c-month').textContent = 'R$ ' + j.cost_month_brl.toLocaleString('pt-BR', {minimumFractionDigits:2});
        
        const top = document.getElementById('top-cnjs');
        top.innerHTML = j.top_cnj_alerts.map(x => `
            <div class="d-flex justify-content-between mb-1 border-bottom border-light border-opacity-10 pb-1">
                <a href="/ui/processo/${x.cnj}" class="text-decoration-none small">${x.cnj}</a>
                <span class="badge bg-warning text-dark">${x.c}</span>
            </div>
        `).join('') || '<div class="muted small">Nada ainda.</div>';
    }
}

async function loadAlerts() {
    const r = await fetch('/ui/api/alerts?limit=10');
    const j = await r.json();
    const list = document.getElementById('alerts-list');
    if(j.ok && j.items.length) {
        list.innerHTML = j.items.map(x => `
            <div class="mb-3 border-bottom border-light border-opacity-10 pb-2">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="badge badge-soft">${x.tipo_inferido}</span>
                    <span class="muted small">${x.data}</span>
                </div>
                <div class="fw-bold small mb-1"><a href="/ui/processo/${x.cnj}" class="text-light text-decoration-none">${x.cnj}</a></div>
                <div class="muted small">${x.texto.substring(0, 200)}...</div>
            </div>
        `).join('');
    } else {
        list.innerHTML = '<div class="text-center py-4 muted">Nenhum alerta relevante.</div>';
    }
}

loadMetrics();
loadAlerts();
setInterval(loadMetrics, 30000);
</script>
"""

ADMIN_BODY = """
<div class="card p-3">
    <div class="h5 mb-3">Painel Administrativo</div>
    <div class="row g-3">
        <div class="col-md-6">
            <div class="card p-3 border-opacity-10">
                <div class="h6">Background Services</div>
                <div id="bg-status" class="small muted mb-3">Carregando status...</div>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-light" onclick="refreshStatus()">Atualizar Status</button>
                    <button class="btn btn-sm btn-outline-primary" onclick="runDiscovery()">Rodar Discover Manual</button>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card p-3 border-opacity-10">
                <div class="h6">Importar Extrato (Custos)</div>
                <textarea id="extrato-raw" class="form-control form-control-sm mb-2 mono" rows="4" placeholder="Cole as linhas do extrato aqui..."></textarea>
                <button class="btn btn-sm btn-primary" onclick="importCosts()">Processar Extrato</button>
                <div id="import-res" class="small mt-2"></div>
            </div>
        </div>
    </div>
</div>

<script>
async function refreshStatus() {
    const r = await fetch('/ui/api/dashboard/metrics');
    const j = await r.json();
    const div = document.getElementById('bg-status');
    if(j.ok) {
        div.innerHTML = `
            Poller Loop: <span class="${j.poll_state.running ? 'text-success':'text-danger'}">${j.poll_state.running ? 'Running':'Stopped'}</span><br>
            Discover Loop: <span class="${j.discover_state.running ? 'text-success':'text-danger'}">${j.discover_state.running ? 'Running':'Stopped'}</span><br>
            Último erro API: ${j.last_api_error ? '<span class="text-warning">'+j.last_api_error.message+'</span>' : 'Nenhum'}
        `;
    }
}

async function runDiscovery() {
    await fetch('/ui/api/discover/run-once', {method: 'POST'});
    alert('Descoberta iniciada em background.');
    refreshStatus();
}

async function importCosts() {
    const text = document.getElementById('extrato-raw').value;
    const resDiv = document.getElementById('import-res');
    resDiv.textContent = 'Importando...';
    const r = await fetch('/ui/api/costs/import', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: text})
    });
    const j = await r.json();
    if(j.ok) {
        resDiv.innerHTML = `<span class="text-success">Sucesso: ${j.count} linhas importadas (+ ${j.errors} erros).</span>`;
        document.getElementById('extrato-raw').value = '';
    } else {
        resDiv.innerHTML = `<span class="text-danger">Erro: ${j.error}</span>`;
    }
}
refreshStatus();
</script>
"""

WATCHLIST_BODY = """
<div class="card p-3 mb-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <div class="h5 mb-0">Watchlist</div>
        <div class="d-flex gap-2">
            <input type="text" id="doc-add" class="form-control form-control-sm" placeholder="CPF ou CNPJ">
            <button class="btn btn-sm btn-primary" onclick="addDoc()">Adicionar</button>
        </div>
    </div>
    <div id="wl-container" class="small">
        <div class="text-center py-4 muted"><span class="spinner-border spinner-border-sm me-2"></span>Carregando...</div>
    </div>
</div>

<script>
async function loadWL() {
    const r = await fetch('/api/v2/watchlist');
    const j = await r.json();
    const cont = document.getElementById('wl-container');
    if(j.ok) {
        cont.innerHTML = `
            <table class="table table-dark table-hover table-sm small">
                <thead><tr><th>Documento</th><th>Tipo</th><th>Ações</th></tr></thead>
                <tbody>
                    ${j.items.map(x => `
                        <tr>
                            <td class="mono">${x.doc}</td>
                            <td>${x.tipo_doc}</td>
                            <td>
                                <button class="btn btn-mini btn-outline-primary" onclick="discoverDoc('${x.doc}')">Descobrir</button>
                                <button class="btn btn-mini btn-outline-danger" onclick="removeDoc(${x.id})">X</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }
}

async function addDoc() {
    const doc = document.getElementById('doc-add').value;
    if(!doc) return;
    await fetch('/api/v2/watchlist', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({doc: doc})
    });
    document.getElementById('doc-add').value = '';
    loadWL();
}

async function discoverDoc(doc) {
    await fetch(`/ui/api/discover/doc/${encodeURIComponent(doc)}`, {method: 'POST'});
    alert('Busca por processos para ' + doc + ' iniciada.');
}

async function removeDoc(id) {
    if(!confirm('Remover monitoramento?')) return;
    await fetch(`/api/v2/watchlist/${id}`, {method: 'DELETE'});
    loadWL();
}

loadWL();
</script>
"""

PROCESS_BODY = """
<div class="row g-3">
    <div class="col-md-4">
        <div id="side-summary" class="card p-3 mb-3 sticky-top" style="top: 1rem; z-index: 10;">
            <div id="side-summary-content">
                <div class="text-center py-4 muted"><span class="spinner-border spinner-border-sm me-2"></span>Carregando resumo...</div>
            </div>
            <hr class="divider">
            <div class="d-grid gap-2">
                <button id="btn-sync" class="btn btn-primary btn-sm">Sincronizar agora</button>
            </div>
        </div>
    </div>
    <div class="col-md-8">
        <ul class="nav nav-tabs mb-3" id="procTabs" role="tablist">
            <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#pane-movs">Timeline</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#pane-capa">Capa Detalhada</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#pane-docs">Documentos</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#pane-pedmult">Pedidos & Multas</button></li>
        </ul>
        <div class="tab-content">
            <div class="tab-pane fade show active" id="pane-movs">
                <div class="card p-3">
                    <div id="movs-box">Carregando timeline...</div>
                </div>
            </div>
            <div class="tab-pane fade" id="pane-capa">
                <div class="card p-3">
                    <div id="capa-box">Carregando capa...</div>
                </div>
            </div>
            <div class="tab-pane fade" id="pane-docs">
                <div class="card p-3">
                    <div class="d-flex justify-content-between mb-2">
                        <div class="h6">Documentos</div>
                        <button class="btn btn-sm btn-outline-primary" onclick="loadDocs()">Atualizar</button>
                    </div>
                    <div id="docs-box">Carregando documentos...</div>
                </div>
            </div>
            <div class="tab-pane fade" id="pane-pedmult">
                <div class="card p-3">
                    <div id="pedidos-box">Carregando...</div>
                    <hr class="divider">
                    <div id="multas-box">Carregando...</div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
const CNJ = "{{ cnj }}";

async function loadCapa() {
    const r = await fetch(`/ui/api/processo/${encodeURIComponent(CNJ)}/capa`);
    const j = await r.json();
    const side = document.getElementById('side-summary-content');
    const capa = document.getElementById('capa-box');
    if(j.ok) {
        const d = j.data;
        side.innerHTML = `
            <div class="h5 mb-1 mono small">${d.numero_cnj}</div>
            <div class="badge badge-soft mb-2">${d.status_predito || 'Ativo'}</div>
            <div class="small muted mb-1"><b>Assunto:</b> ${d.assunto_principal_normalizado || '-'}</div>
            <div class="small muted mb-1"><b>Tribunal:</b> ${d.tribunal?.nome || '-'}</div>
        `;
        capa.innerHTML = `<pre class="small text-muted">${JSON.stringify(d, null, 2)}</pre>`;
    }
}

async function loadMovs() {
    const r = await fetch(`/ui/api/processo/${encodeURIComponent(CNJ)}/movimentacoes?limit=50`);
    const j = await r.json();
    const box = document.getElementById('movs-box');
    if(j.ok) {
        box.innerHTML = j.items.map(x => `
            <div class="mb-3 border-bottom border-light border-opacity-10 pb-2">
                <div class="d-flex justify-content-between small mb-1">
                    <span class="badge ${x.tipo_inferido ? 'bg-warning text-dark':'bg-secondary'}">${x.tipo_inferido || 'MOV'}</span>
                    <span class="muted">${x.data}</span>
                </div>
                <div class="small">${x.texto}</div>
            </div>
        `).join('') || '<div class="muted">Sem movimentações.</div>';
    }
}

async function loadDocs() {
     const r = await fetch(`/ui/api/processo/${encodeURIComponent(CNJ)}/documentos`);
     const j = await r.json();
     const box = document.getElementById('docs-box');
     if(j.ok) {
         box.innerHTML = j.items.map(x => `
            <div class="d-flex justify-content-between align-items-center mb-2 p-2 bg-light bg-opacity-5 rounded">
                <div class="small">${x.titulo || 'Documento'}</div>
                <a href="/ui/api/processo/${encodeURIComponent(CNJ)}/documentos/${x.doc_key}/download" class="btn btn-mini btn-outline-primary">Download</a>
            </div>
         `).join('') || '<div class="muted">Nenhum documento encontrado.</div>';
     }
}

document.getElementById('btn-sync').onclick = async () => {
    const btn = document.getElementById('btn-sync');
    btn.disabled = true;
    btn.textContent = 'Sincronizando...';
    await fetch(`/ui/api/processo/${encodeURIComponent(CNJ)}/sync`, {method: 'POST'});
    btn.disabled = false;
    btn.textContent = 'Sincronizar agora';
    loadMovs();
    loadCapa();
};

loadCapa();
loadMovs();
loadDocs();
</script>
"""
