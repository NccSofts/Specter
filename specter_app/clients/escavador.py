import time
import requests
from typing import Any, Dict, Optional
from ..config import ESCAVADOR_BASE, ESCAVADOR_TOKEN
from ..database import record_api_usage, estimate_cost_brl
from ..utils.logger import logger, redact_secrets
from ..utils.helpers import utcnow_iso, extract_list, normalize_doc

class EscavadorClient:
    def __init__(self, base: str = ESCAVADOR_BASE, token: str = ESCAVADOR_TOKEN):
        self.base = base.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "BlueService-EscavadorMonitor/4.3",
            }
        )

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        timeout: int = 45,
        retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> Dict[str, Any]:
        url = self._url(path)
        last_exc: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                if method.upper() == "GET":
                    r = self.session.get(url, params=params, timeout=timeout)
                else:
                    r = self.session.request(method.upper(), url, params=params, json=payload, timeout=timeout)

                if r.status_code == 429 or 500 <= r.status_code <= 599:
                    logger.warning("Escavador %s %s attempt=%s status=%s: %s", method, path, attempt, r.status_code, r.text[:400])
                    if attempt < retries:
                        time.sleep(backoff_seconds * attempt)
                        continue

                if r.status_code == 422:
                    # 422 Unprocessable Content: usually means "Already monitored" or validation error.
                    # We return the JSON but do NOT retry or raise.
                    return r.json()

                if r.status_code >= 400:
                    logger.error("Escavador %s %s failed %s: %s", method, path, r.status_code, r.text[:1200])
                    r.raise_for_status()

                if not (r.text or "").strip():
                    return {}

                return r.json()

            except requests.exceptions.RequestException as e:
                last_exc = e
                logger.warning("Escavador %s %s attempt=%s network_error=%s", method, path, attempt, repr(e)[:400])
                if attempt < retries:
                    time.sleep(backoff_seconds * attempt)
                    continue
                raise

        if last_exc:
            raise last_exc
        return {}

    def post(self, path: str, payload: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request_json("POST", path, params=params, payload=payload)

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request_json("GET", path, params=params)

    def criar_monitor_novos_processos(self, termo: str) -> Dict[str, Any]:
        return self.post("/monitoramentos/novos-processos", {"termo": termo})

    def criar_monitor_processo(self, numero_cnj: str) -> Dict[str, Any]:
        return self.post("/monitoramentos/processos", {"numero": numero_cnj})

    def listar_movimentacoes(self, numero_cnj: str, limit: int = 100) -> Dict[str, Any]:
        service_key = "v2_movimentacoes_processo"
        endpoint = f"/processos/numero_cnj/{numero_cnj}/movimentacoes"
        status = None
        data: Dict[str, Any] = {}
        try:
            data = self.get(endpoint, {"limit": limit})
            status = 200
            return data
        except requests.exceptions.HTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            raise
        finally:
            items = len(extract_list(data))
            cost = estimate_cost_brl(service_key, items_upto=items)
            record_api_usage(doc=None, cnj=numero_cnj, service_key=service_key, endpoint=endpoint, http_status=status, items_count=items, cost_brl=cost)

    def obter_capa_processo(self, numero_cnj: str) -> Dict[str, Any]:
        service_key = "v2_capa_processo"
        endpoint = f"/processos/numero_cnj/{numero_cnj}"
        status = None
        try:
            data = self.get(endpoint, params=None)
            status = 200
            return data
        except requests.exceptions.HTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            raise
        finally:
            cost = estimate_cost_brl(service_key, items_upto=0)
            record_api_usage(doc=None, cnj=numero_cnj, service_key=service_key, endpoint=endpoint, http_status=status, items_count=0, cost_brl=cost)

    def listar_processos_envolvido(self, cpf_cnpj: str, limit: int = 50, page: Optional[int] = None) -> Dict[str, Any]:
        service_key = "v2_processos_envolvido"
        params: Dict[str, Any] = {"cpf_cnpj": cpf_cnpj, "limit": limit}
        if page is not None:
            params["page"] = page
        endpoint = "/envolvido/processos"
        status = None
        data: Dict[str, Any] = {}
        try:
            data = self.get(endpoint, params=params)
            status = 200
            return data
        except requests.exceptions.HTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            raise
        finally:
            items = len(extract_list(data))
            p = int(page or 1)
            items_upto = (max(p-1, 0) * int(limit)) + items
            cost = estimate_cost_brl(service_key, items_upto=items_upto)
            record_api_usage(doc=normalize_doc(cpf_cnpj), cnj=None, service_key=service_key, endpoint=endpoint, http_status=status, items_count=items, cost_brl=cost, notes=f"limit={limit} page={p}")

    def listar_callbacks(self, limit: int = 100, page: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit}
        if page is not None:
            params["page"] = page
        return self.get("/callbacks", params=params)

    def listar_documentos_publicos_v2(self, numero_cnj: str, limit: int = 50, page: int = 1) -> Dict[str, Any]:
        limit_n = 100 if int(limit) == 100 else 50
        page_n = max(1, int(page))
        endpoint = f"/processos/numero_cnj/{numero_cnj}/documentos-publicos"
        return self.get(endpoint, {"limit": limit_n, "page": page_n})

    def listar_autos_v2(self, numero_cnj: str, limit: int = 50, page: int = 1) -> Dict[str, Any]:
        limit_n = 100 if int(limit) == 100 else 50
        page_n = max(1, int(page))
        endpoint = f"/processos/numero_cnj/{numero_cnj}/autos"
        return self.get(endpoint, {"limit": limit_n, "page": page_n})

    def solicitar_atualizacao_v2(
        self,
        numero_cnj: str,
        tipo_atualizacao: str = "PUBLICA",
        send_callback: int = 0,
        usuario: Optional[str] = None,
        senha: Optional[str] = None,
        certificado_id: Optional[int] = None,
        documentos_especificos: Optional[str] = None,
    ) -> Dict[str, Any]:
        endpoint = f"/processos/numero_cnj/{numero_cnj}/solicitar-atualizacao"
        params: Dict[str, Any] = {}
        if send_callback == 1:
            params["send_callback"] = 1

        payload: Dict[str, Any] = {
            "tipo_atualizacao": tipo_atualizacao.upper(),
        }
        if tipo_atualizacao.upper() == "RESTRITO":
            if usuario: payload["usuario"] = str(usuario)
            if senha: payload["senha"] = str(senha)
            if certificado_id is not None: payload["certificado_id"] = int(certificado_id)
            if documentos_especificos: payload["documentos_especificos"] = str(documentos_especificos)

        return self.post(endpoint, payload, params=params or None)

    def status_atualizacao_v2(self, numero_cnj: str) -> Dict[str, Any]:
        endpoint = f"/processos/numero_cnj/{numero_cnj}/status-atualizacao"
        return self.get(endpoint)

    def baixar_documento_pdf_v2(self, numero_cnj: str, key: str) -> requests.Response:
        endpoint = f"/processos/numero_cnj/{numero_cnj}/documentos/{key}"
        return self._request_raw("GET", endpoint)

    def _request_raw(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url = self._url(path)
        r = self.session.request(method, url, params=params, timeout=45)
        r.raise_for_status()
        return r
