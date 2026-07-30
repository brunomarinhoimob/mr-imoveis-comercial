import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests


DEFAULT_BASE_URL = "https://api.pipe.run/v1"


def get_piperun_token() -> str:
    """
    Reads the PipeRun token from Streamlit secrets or environment variables.
    Never hard-code the token in the repository.
    """
    token = ""

    try:
        import streamlit as st

        token = str(st.secrets.get("PIPERUN_TOKEN", "") or "").strip()
    except Exception:
        token = ""

    if not token:
        token = str(os.getenv("PIPERUN_TOKEN", "") or "").strip()

    return token


def get_piperun_base_url() -> str:
    try:
        import streamlit as st

        base_url = str(st.secrets.get("PIPERUN_API_BASE", "") or "").strip()
    except Exception:
        base_url = ""

    if not base_url:
        base_url = str(os.getenv("PIPERUN_API_BASE", "") or "").strip()

    return (base_url or DEFAULT_BASE_URL).rstrip("/")


def get_piperun_activities_export_url() -> str:
    try:
        import streamlit as st

        export_url = str(st.secrets.get("PIPERUN_ACTIVITIES_EXPORT_URL", "") or "").strip()
    except Exception:
        export_url = ""

    if not export_url:
        export_url = str(os.getenv("PIPERUN_ACTIVITIES_EXPORT_URL", "") or "").strip()

    return export_url


@dataclass
class PiperunFetchResult:
    endpoint: str
    data: pd.DataFrame
    ok: bool
    status_code: Optional[int] = None
    next_cursor: str = ""
    error: str = ""


class PiperunClient:
    """
    Small defensive PipeRun API client.

    PipeRun accounts may expose slightly different resource names depending on
    plan/version. This client tries common endpoint candidates and returns the
    first useful payload. If needed, change the candidate lists in the page.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        self.token = (token or get_piperun_token()).strip()
        self.base_url = (base_url or get_piperun_base_url()).rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    def _extract_records(self, payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]

        if not isinstance(payload, dict):
            return []

        for key in ("data", "items", "results", "records", "rows"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
            if isinstance(value, dict):
                nested = self._extract_records(value)
                if nested:
                    return nested

        return [payload] if payload else []

    def _extract_next_cursor(self, payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""

        candidates = [
            payload.get("next_cursor"),
            payload.get("nextCursor"),
            payload.get("cursor"),
            payload.get("next"),
        ]

        meta = payload.get("meta")
        if isinstance(meta, dict):
            candidates.extend(
                [
                    meta.get("next_cursor"),
                    meta.get("nextCursor"),
                    meta.get("cursor"),
                    meta.get("next"),
                ]
            )

        links = payload.get("links")
        if isinstance(links, dict):
            candidates.extend([links.get("next_cursor"), links.get("nextCursor"), links.get("next")])

        for value in candidates:
            if value:
                return str(value)
        return ""

    def _request_once(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        auth_mode: str = "bearer",
    ) -> Tuple[Optional[requests.Response], str]:
        url = f"{self.base_url}/{endpoint.strip('/')}"
        params = dict(params or {})
        headers = self._headers()

        if auth_mode == "query":
            headers.pop("Authorization", None)
            params.setdefault("token", self.token)

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=self.timeout,
            )
            return response, ""
        except requests.RequestException as exc:
            return None, str(exc)

    def download_file(
        self,
        url: str,
        destination: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        if not self.configured:
            return False, "PIPERUN_TOKEN nao configurado."
        if not url:
            return False, "PIPERUN_ACTIVITIES_EXPORT_URL nao configurada."

        final_url = url if url.startswith("http") else f"{self.base_url}/{url.strip('/')}"
        query = dict(params or {})
        last_error = ""

        for auth_mode in ("bearer", "query"):
            headers = self._headers()
            request_params = dict(query)
            if auth_mode == "query":
                headers.pop("Authorization", None)
                request_params.setdefault("token", self.token)

            try:
                response = requests.get(final_url, headers=headers, params=request_params, timeout=max(self.timeout, 90))
            except requests.RequestException as exc:
                last_error = str(exc)
                continue

            if response.status_code >= 400:
                last_error = f"HTTP {response.status_code}: {response.text[:300]}"
                continue

            content = response.content or b""
            if len(content) < 100:
                last_error = "Resposta vazia ou pequena demais para ser uma planilha."
                continue

            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with open(destination, "wb") as file:
                file.write(content)
            return True, destination

        return False, last_error or "Nao foi possivel baixar a exportacao."


    def get_page(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        page: int = 1,
        per_page: int = 100,
    ) -> PiperunFetchResult:
        if not self.configured:
            return PiperunFetchResult(endpoint=endpoint, data=pd.DataFrame(), ok=False, error="PIPERUN_TOKEN nao configurado.")

        query = dict(params or {})
        query.setdefault("page", page)
        query.setdefault("pagina", page)
        query.setdefault("show", per_page)
        query.setdefault("per_page", per_page)
        query.setdefault("limit", per_page)
        query.setdefault("size", per_page)

        last_error = ""
        last_status = None

        for auth_mode in ("bearer", "query"):
            response, error = self._request_once(endpoint, query, auth_mode=auth_mode)
            if error:
                last_error = error
                continue
            if response is None:
                continue

            last_status = response.status_code
            if response.status_code in (401, 403):
                last_error = f"HTTP {response.status_code}: token sem acesso ou modo de autenticacao nao aceito."
                continue

            if response.status_code >= 400:
                last_error = f"HTTP {response.status_code}: {response.text[:300]}"
                continue

            try:
                payload = response.json()
            except ValueError:
                last_error = "Resposta nao e JSON."
                continue

            records = self._extract_records(payload)
            next_cursor = self._extract_next_cursor(payload)
            return PiperunFetchResult(
                endpoint=endpoint,
                data=pd.json_normalize(records) if records else pd.DataFrame(),
                ok=True,
                status_code=response.status_code,
                next_cursor=next_cursor,
            )

        return PiperunFetchResult(
            endpoint=endpoint,
            data=pd.DataFrame(),
            ok=False,
            status_code=last_status,
            error=last_error or "Nao foi possivel consultar o endpoint.",
        )

    def fetch_first_available(
        self,
        endpoints: Iterable[str],
        params: Optional[Dict[str, Any]] = None,
        max_pages: int = 5,
        per_page: int = 100,
    ) -> PiperunFetchResult:
        errors = []

        for endpoint in endpoints:
            frames = []
            endpoint_ok = False
            last_result = None
            cursor = ""

            for page in range(1, max_pages + 1):
                page_params = dict(params or {})
                if cursor:
                    page_params["cursor"] = cursor
                result = self.get_page(endpoint, params=page_params, page=page, per_page=per_page)
                last_result = result

                if not result.ok:
                    errors.append(f"{endpoint}: {result.error}")
                    break

                endpoint_ok = True
                if result.data.empty:
                    break

                frames.append(result.data)

                if page > 1:
                    current = pd.concat(frames, ignore_index=True)
                    if "id" in current.columns and current["id"].astype(str).duplicated().any():
                        frames.pop()
                        break

                if result.data.empty:
                    break

                cursor = result.next_cursor or ""
                if not cursor and len(result.data) < per_page:
                    break

            if endpoint_ok:
                data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
                return PiperunFetchResult(endpoint=endpoint, data=data, ok=True, status_code=last_result.status_code if last_result else None)

        return PiperunFetchResult(
            endpoint=", ".join(endpoints),
            data=pd.DataFrame(),
            ok=False,
            error=" | ".join(errors[-5:]) or "Nenhum endpoint respondeu com sucesso.",
        )


def date_params(data_ini: date, data_fim: date) -> Dict[str, str]:
    start = data_ini.isoformat()
    end = data_fim.isoformat()
    return {
        "start_date": start,
        "end_date": end,
        "data_inicial": start,
        "data_final": end,
        "created_at_start": start,
        "created_at_end": end,
    }
