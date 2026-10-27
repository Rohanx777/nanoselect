import json
import threading
from urllib.error import HTTPError
from urllib.request import Request,urlopen

import pytest

from src.recommend import load_demo
from src.webapp import APP_ID,LocalServer


@pytest.fixture(scope="module")
def server():
    app=LocalServer(("127.0.0.1",0))
    worker=threading.Thread(target=app.serve_forever,daemon=True)
    worker.start()
    yield f"http://127.0.0.1:{app.server_port}"
    app.shutdown()
    app.server_close()
    worker.join(timeout=5)


def post(server,scenario,**headers):
    request=Request(server+"/api/recommend",data=json.dumps({"scenario":scenario}).encode(),
                    headers={"Content-Type":"application/json",**headers})
    return urlopen(request,timeout=15)


def test_interface_and_assets_are_served_locally(server):
    for path,kind in [("/","text/html"),("/app.js","text/javascript"),("/style.css","text/css")]:
        with urlopen(server+path) as response:
            assert response.status==200
            assert kind in response.headers["Content-Type"]
            assert len(response.read())>100
    with urlopen(server+"/api/health") as response:
        assert json.load(response)["app_id"]==APP_ID


@pytest.mark.parametrize("name,top",[
    ("demo_ml",["M02","M03","M08"]),("demo_dark",["M08"]),
    ("demo_lead",["M13"]),("demo_unknown",[])])
def test_browser_api_preserves_the_real_engine_results(server,name,top):
    with post(server,load_demo(name),Origin=server) as response:
        data=json.load(response)
    assert len(data["rows"])==15
    assert data["summary"]["top_candidates"]==top
    if name=="demo_ml":
        assert sum(row["prediction"] is not None for row in data["rows"])==1
    if name=="demo_unknown":
        assert all(row["score_min"] is None for row in data["rows"])


def test_invalid_inputs_are_actionable_errors(server):
    scenario=dict(load_demo("demo_ml"),pH=99)
    with pytest.raises(HTTPError) as error:
        post(server,scenario)
    assert error.value.code==400
    assert "pH" in json.load(error.value)["error"]


def test_unrelated_origins_and_arbitrary_files_are_not_served(server):
    with pytest.raises(HTTPError) as error:
        post(server,load_demo("demo_ml"),Origin="https://unrelated.example")
    assert error.value.code==403
    with pytest.raises(HTTPError) as error:
        urlopen(server+"/models/tio2_pipeline.joblib")
    assert error.value.code==404
