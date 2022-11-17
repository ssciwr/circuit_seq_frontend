from typing import Dict
import io
import zipfile
from freezegun import freeze_time
import pathlib


@freeze_time("2022-11-14")
def test_remaining_mon(client):
    response = client.get("/remaining")
    assert response.json["remaining"] == 96


@freeze_time("2022-11-19")
def test_remaining_sat(client):
    response = client.get("/remaining")
    assert response.json["remaining"] == 0


def _get_auth_headers(
    client, email: str = "user@embl.de", password: str = "user"
) -> Dict:
    response = client.post("/login", json={"email": email, "password": password})
    token = response.json["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_invalid(client):
    # missing json
    response = client.post("/login")
    assert response.status_code == 400
    # unknown email
    response = client.post("/login", json={"email": "", "password": ""})
    assert response.status_code == 401
    assert response.json == "Unknown email address"
    # wrong password
    response = client.post("/login", json={"email": "user@embl.de", "password": ""})
    assert response.status_code == 401
    assert response.json == "Incorrect password"


def test_login_valid(client):
    email = "user@embl.de"
    password = "user"
    response = client.post("/login", json={"email": email, "password": password})
    assert response.status_code == 200
    assert "access_token" in response.json
    assert response.json["user"]["email"] == email
    assert response.json["user"]["is_admin"] is False


def test_samples_invalid(client):
    # no auth header
    response = client.get("/samples")
    assert response.status_code == 401


def test_samples_valid(client):
    headers = _get_auth_headers(client)
    response = client.get("/samples", headers=headers)
    assert response.status_code == 200
    assert "current_samples" in response.json
    assert "previous_samples" in response.json


def test_running_options_invalid(client):
    # no auth header
    response = client.get("/running_options")
    assert response.status_code == 401


def test_running_options_valid(client):
    headers = _get_auth_headers(client)
    response = client.get("/running_options", headers=headers)
    assert response.status_code == 200
    assert "running_options" in response.json


@freeze_time("2022-11-14")
def test_addsample_mon_fasta(client, ref_seq_fasta):
    headers = _get_auth_headers(client)
    response = client.post(
        "/addsample",
        data={
            "name": "abc",
            "running_option": "r",
            "file": (ref_seq_fasta, "test.fa"),
        },
        headers=headers,
    )
    assert response.status_code == 200
    new_sample = response.json["sample"]
    assert new_sample["email"] == "user@embl.de"
    assert new_sample["name"] == "abc"
    assert new_sample["primary_key"] == "22_46_A1"
    assert new_sample["reference_sequence_description"] == "seq0"
    assert new_sample["running_option"] == "r"
    data_path = pathlib.Path(client.application.config.get("CIRCUITSEQ_DATA_PATH"))
    fasta_path = data_path / "2022/46/inputs/references/22_46_A1_abc.fasta"
    assert fasta_path.is_file()
    with fasta_path.open() as f:
        assert new_sample["reference_sequence_description"] in f.readline()


@freeze_time("2022-11-14")
def test_addsample_mon_fasta_invalid(client):
    headers = _get_auth_headers(client)
    response = client.post(
        "/addsample",
        data={
            "name": "abc",
            "running_option": "r",
            "file": (io.BytesIO(b"invalid_fasta_contents"), "test.fa"),
        },
        headers=headers,
    )
    assert response.status_code == 401
    assert response.json["message"] == "Failed to parse reference sequence file."
    data_path = pathlib.Path(client.application.config.get("CIRCUITSEQ_DATA_PATH"))
    fasta_path = data_path / "2022/46/inputs/references/22_46_A1_abc.fasta"
    assert not fasta_path.is_file()


@freeze_time("2022-11-14")
def test_addsample_mon_embl(client, ref_seq_embl):
    headers = _get_auth_headers(client)
    response = client.post(
        "/addsample",
        data={
            "name": "abc",
            "running_option": "r",
            "file": (ref_seq_embl, "test.embl"),
        },
        headers=headers,
    )
    assert response.status_code == 200
    new_sample = response.json["sample"]
    assert new_sample["email"] == "user@embl.de"
    assert new_sample["name"] == "abc"
    assert new_sample["primary_key"] == "22_46_A1"
    assert new_sample["reference_sequence_description"] == "X56734.1"
    assert new_sample["running_option"] == "r"
    data_path = pathlib.Path(client.application.config.get("CIRCUITSEQ_DATA_PATH"))
    fasta_path = data_path / "2022/46/inputs/references/22_46_A1_abc.fasta"
    assert fasta_path.is_file()
    with fasta_path.open() as f:
        assert new_sample["reference_sequence_description"] in f.readline()


@freeze_time("2022-11-14")
def test_addsample_mon_genbank(client, ref_seq_genbank):
    headers = _get_auth_headers(client)
    response = client.post(
        "/addsample",
        data={
            "name": "abc",
            "running_option": "r",
            "file": (ref_seq_genbank, "test.gbk"),
        },
        headers=headers,
    )
    assert response.status_code == 200
    new_sample = response.json["sample"]
    assert new_sample["email"] == "user@embl.de"
    assert new_sample["name"] == "abc"
    assert new_sample["primary_key"] == "22_46_A1"
    assert new_sample["reference_sequence_description"] == "Z78533.1"
    assert new_sample["running_option"] == "r"
    data_path = pathlib.Path(client.application.config.get("CIRCUITSEQ_DATA_PATH"))
    fasta_path = data_path / "2022/46/inputs/references/22_46_A1_abc.fasta"
    assert fasta_path.is_file()
    with fasta_path.open() as f:
        assert new_sample["reference_sequence_description"] in f.readline()


def test_admin_settings_invalid(client):
    # no auth header
    response = client.get("/admin/settings")
    assert response.status_code == 401
    # valid non-admin user auth header
    headers = _get_auth_headers(client)
    response = client.get("/admin/settings", headers=headers)
    assert response.status_code == 401


def test_admin_settings_valid(client):
    headers = _get_auth_headers(client, "admin@embl.de", "admin")
    response = client.get("/admin/settings", headers=headers)
    assert response.status_code == 200
    assert response.json["plate_n_rows"] == 8
    assert response.json["plate_n_cols"] == 12
    # set new valid settings
    response = client.post(
        "/admin/settings",
        json={
            "plate_n_rows": 14,
            "plate_n_cols": 18,
            "running_options": ["o1", "o2", "o3"],
            "last_submission_day": 4,
        },
        headers=headers,
    )
    assert response.status_code == 200
    response = client.get("/admin/settings", headers=headers)
    assert response.status_code == 200
    assert response.json["plate_n_rows"] == 14
    assert response.json["plate_n_cols"] == 18
    assert response.json["running_options"] == ["o1", "o2", "o3"]
    assert response.json["last_submission_day"] == 4


def test_admin_allsamples_invalid(client):
    # no auth header
    response = client.get("/admin/allsamples")
    assert response.status_code == 401
    # valid non-admin user auth header
    headers = _get_auth_headers(client)
    response = client.get("/admin/allsamples", headers=headers)
    assert response.status_code == 401


def test_admin_allsamples_valid(client):
    headers = _get_auth_headers(client, "admin@embl.de", "admin")
    response = client.get("/admin/allsamples", headers=headers)
    assert response.status_code == 200
    assert "current_samples" in response.json
    assert "previous_samples" in response.json


def test_admin_allusers_invalid(client):
    # no auth header
    response = client.get("/admin/allusers")
    assert response.status_code == 401
    # valid non-admin user auth header
    headers = _get_auth_headers(client)
    response = client.get("/admin/allusers", headers=headers)
    assert response.status_code == 401


def test_admin_allusers_valid(client):
    headers = _get_auth_headers(client, "admin@embl.de", "admin")
    response = client.get("/admin/allusers", headers=headers)
    assert response.status_code == 200
    assert "users" in response.json


def test_admin_zipsamples_invalid(client):
    # no auth header
    response = client.post("/admin/zipsamples")
    assert response.status_code == 401
    # valid non-admin user auth header
    headers = _get_auth_headers(client)
    response = client.post("/admin/zipsamples", headers=headers)
    assert response.status_code == 401


def test_admin_zipsamples_valid(client):
    headers = _get_auth_headers(client, "admin@embl.de", "admin")
    response = client.post("/admin/zipsamples", headers=headers)
    assert response.status_code == 200
    zip_file = zipfile.ZipFile(io.BytesIO(response.data))
    assert len(zip_file.filelist) == 1
    assert zip_file.filelist[0].filename == "samples.tsv"
    tsv = zip_file.read("samples.tsv")
    assert tsv == b"date\tprimary_key\temail\tname\trunning_option\n"
