import httpx
import pytest
from fastapi import FastAPI
from fastapi.requests import Request
from starlette import status

from fastapi_cache.decorator import cache

pytestmark = pytest.mark.anyio


@pytest.mark.usefixtures("disable_cache")
async def test_no_request(http_client: httpx.AsyncClient, app: FastAPI):
    @app.get("/no-request")
    @cache()
    async def _endpoint():
        pass

    @app.get("/request")
    @cache()
    async def _endpoint(request_parameter: Request):
        assert isinstance(request_parameter, Request)

    response = await http_client.get("/no-request")
    assert response.status_code == status.HTTP_200_OK

    response = await http_client.get("/request")
    assert response.status_code == status.HTTP_200_OK
